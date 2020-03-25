
from django.conf import settings

import os
import json
import datetime
import logging
import redis
import socket
import pprint
import base64

try:
	import version
	version_number, version_svn_rev = version.number, version.svn_rev
except ImportError:
	version_number, version_svn_rev = 0, 0

from phabricator import Phabricator
from django.http import HttpRequest
from django.utils import timezone

from .CatchExceptions import CatchExceptions, GetEnvInfo
from ...io.hash import Hash32, Hash
from ...io import converters
from ...utils.backtrace import GetTraceback
from ...utils.ph import Ph, ph_upload_file_get_id


POOL = None
LIMIT_DAILY_REPORTS = 200
LIMIT_HOURLY_REPORTS = 20


log = logging.getLogger(__name__)

maniphest = settings.PHABRICATOR_SINK['maniphest']
ph_api = settings.PHABRICATOR_SINK['api']
ttl = settings.PHABRICATOR_SINK['ttl']

redis_master_key = 'HTTP50x-Ph-{}'
redis_title_key = 'BUG-Ph-{}'
redis_counter = 'Ph-cnt-{}'


def FormatDescription(key, traceback, request=None, config=None):

	description = "Process:\n```{}```\n".format(GetEnvInfo(request))

	if traceback:
		description += "\n\nTraceback:\n```lang=py3tb\n{}```".format(traceback)

	if config:
		description += "\n\nConfig:\n```lang=python3\n{}```".format(pprint.pformat(config))

	if request is not None and isinstance(request, HttpRequest):

		description += "\n\nMETA:\n```lang=python3\n{}```".format(pprint.pformat(request.META))
		if request.POST:
			description += "\n\nPOST:\n```lang=python3\n{}```".format(pprint.pformat(request.POST))
		if request.COOKIES:
			description += "\n\nCOOKIES:\n```lang=python3\n{}```".format(pprint.pformat(request.COOKIES))

	description += "\n\nBug hash: `{}`".format(key)

	return description


def UploadFileToPhabricator(api, fname, content):
	"""
	fname -- file name
	content -- must be bytes
	return -- phabricator file id
	"""
	ph = Ph(url=api['url'], token=api['token'])
	return ph_upload_file_get_id(ph,
		name=fname,
		data_base64=base64.b64encode(content),
		viewPolicy=maniphest['viewPolicy'],
		canCDN='false'
	)


def ReportToPhabricator(endpoint_hash, title, description, conduit_gateway=None, upload_files=None, title_hash=None):
	"""
	upload_files -- [(filename, bytes), ...]
	"""
	if not POOL:
		log.error("PhabricatorSink: ReportBug: redis is not initialized")
		return False

	title_org = title
	if title and len(title) > 200:
		title = title[:200] + "…"

	key = redis_master_key.format(endpoint_hash)
	redis_conn = redis.Redis(connection_pool=POOL)

	if redis_conn.get(key):
		log.warning(f"Phabricator task \"{title}\" already exists: {key}")
		return False

	if title_hash and redis_conn.get(redis_title_key.format(title_hash)):
		# Prevent reporting the same issues, like connection problems to DB,
		# where each report is originated from different location in the code (unique backtrace)
		# but the title (exception message) and the last line shoule be the same.
		log.warning(f"Phabricator task for title \"{title}\" already exists: {title_hash}")
		return False

	now = timezone.now()

	with redis_conn.pipeline() as pipe:

		daily_key = redis_counter.format(now.strftime('%y%m%d'))
		hourly_key = redis_counter.format(now.strftime('%y%m%d%H'))
		pipe.incr(daily_key)
		pipe.incr(hourly_key)

		pipe.expire(daily_key, 24 * 60 * 60)
		pipe.expire(hourly_key, 60 * 60)

		daily, hourly, *_ = pipe.execute()

	if daily > LIMIT_DAILY_REPORTS:
		log.warning(f"Phabricator task \"{title}\" failed to report: daily limit {LIMIT_DAILY_REPORTS} exeeded")
		return False

	if hourly > LIMIT_HOURLY_REPORTS:
		log.warning(f"Phabricator task \"{title}\" failed to report: hourly limit {LIMIT_HOURLY_REPORTS} exeeded")
		return False

	api = ph_api[conduit_gateway or 'default']

	ph = Phabricator(host=api['url'], token=api['token'])

	if upload_files is not None:
		attach_desc = ['\n\nAttachments:\n']
		for fname, content in upload_files:
			ret_id = UploadFileToPhabricator(api, fname, content)
			attach_desc.append('{' + "F{}".format(str(ret_id)) + '}\n')
	else:
		attach_desc = []

	task = ph.maniphest.createtask(
		title=title,
		description=description + ''.join(attach_desc),
		ownerPHID=api.get('owner') or maniphest.get('owner'),
		viewPolicy=maniphest['viewPolicy'],
		editPolicy=maniphest['editPolicy'],
		projectPHIDs=[maniphest['project']]
	)

	# <Result: {
	# 	'id': '4331',
	# 	'phid': 'PHID-TASK-myofuodmwwca266qrgaj',
	# 	'authorPHID': 'PHID-USER-dylescmxfosc3u4qmc7c',
	# 	'ownerPHID': None,
	# 	'ccPHIDs': ['PHID-USER-dylescmxfosc3u4qmc7c'],
	# 	'status': 'open',
	# 	'statusName': 'Open',
	# 	'isClosed': False,
	# 	'priority': 'Normal',
	# 	'priorityColor': 'orange',
	# 	'title': 'HTTP500: parafie.wre.pl:8000/',
	# 	'description': '...Bug hash: ``HTTP50x-Ph-`',
	# 	'projectPHIDs': ['PHID-PROJ-kjcsoux56jqgupqly4ao'],
	# 	'uri': 'http://phabricator.tru.pl/T4331',
	# 	'auxiliary': [],
	# 	'objectName': 'T4331',
	# 	'dateCreated': '1522223793',
	# 	'dateModified': '1522223793',
	# 	'dependsOnTaskPHIDs': []
	# }>

	log.warning("Phabricator task created: {} {}".format(task['objectName'], task['uri']))
	with redis_conn.pipeline() as pipe:
		pipe.set(key, json.dumps({"task": task['objectName'], "created": converters.datetime2json(now)}))
		pipe.expire(key, ttl)
		pipe.execute()

	return True


def ReportBug(title, ex, traceback, config=None, request=None, conduit_gateway=None, upload_files=None):

	title_hash = title or ''
	traceback_to_hash = traceback
	if traceback_to_hash:
		# The last line of the traceback is removed due to limit reports of the same expection but with different final messages
		bt = traceback_to_hash.split('\n')
		traceback_to_hash = '\n'.join(bt[:-1])

		if title_hash:
			title_hash += '\n'

		title_hash += bt[-1]

	endpoint_hash = Hash32(traceback_to_hash)
	description = FormatDescription(endpoint_hash, traceback, config=config, request=request)
	return ReportToPhabricator(endpoint_hash, title, description, conduit_gateway=conduit_gateway, upload_files=upload_files, title_hash=Hash32(title_hash))


def PhabricatorSink(get_response):

	@CatchExceptions
	def process_request(request):

		response = get_response(request)

		if not settings.DEBUG and response.status_code >= 500 and response.status_code <= 599 and not hasattr(response, "skip_bug_report") and getattr(request, "_exception_reported", False) is not True:

			try:
				if hasattr(response, '_exc_details'):
					exc, traceback = response._exc_details
				else:
					exc = None
					traceback = None

				ReportBug("HTTP{}: {}".format(response.status_code, request.full_url), exc, request=request, traceback=traceback, conduit_gateway='backend')
			except Exception as ex:
				logging.exception("Cannot report bug")

		return response

	return process_request
