
from django.conf import settings

import os
import json
import datetime
import logging
import redis
import socket
import pprint

try:
	import version
	version_number, version_svn_rev = version.number, version.svn_rev
except ImportError:
	version_number, version_svn_rev = 0, 0

from phabricator import Phabricator
from django.http import HttpRequest

from .CatchExceptions import CatchExceptions
from ...io.hash import Hash32
from ...io import converters
from ...utils.backtrace import GetTraceback


POOL = None

log = logging.getLogger(__name__)

maniphest = settings.PHABRICATOR_SINK['maniphest']
redis_master_key = 'HTTP50x-Ph-{}'
ph_api = settings.PHABRICATOR_SINK['api']
ttl = settings.PHABRICATOR_SINK['ttl']

hostname = socket.gethostname()


def GetProcessInfo(request=None):
	r = '';
	r += 'PID: `{}` (`{}`)\nHOST: `{}`\nVERSION: `{}` (svn: `{}`)\n'.format(os.getpid(), settings.SERVER_ID, hostname, version_number, version_svn_rev)

	if request is not None:
		environ = request.environ if hasattr(request, 'environ') else {}
		profile = request._cached_profile if hasattr(request, '_cached_profile') else None
		META = request.META if hasattr(request, 'META') else {}
		COOKIES = request.COOKIES if hasattr(request, 'COOKIES') else {}

		r += 'URL: `%s`\nUSER_AGENT: `%s`\nUSER: `%s`\nREMOTE_ADDR: `%s`\nCURRENT_ENDPOINT: `%s`\nMETHOD: `%s`\nCOOKIES: `%s`\n' % (
			request.build_absolute_uri(),
			META.get('HTTP_USER_AGENT', 'NONE'),
			profile,
			META.get('REMOTE_ADDR', 'NONE'),
			getattr(request, 'CURRENT_ENDPOINT', None),
			getattr(request, 'method', None),
			COOKIES
		)

	return r


def FormatDescription(key, traceback, request=None, config=None):

	description = "Process:\n```{}```\n".format(GetProcessInfo(request))
	
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


def ReportToPhabricator(endpoint_hash, title, description, conduit_gateway=None):

	if not POOL:
		log.error("PhabricatorSink: ReportBug: redis is not initialized")
		return False

	key = redis_master_key.format(endpoint_hash)
	redis_conn = redis.Redis(connection_pool=POOL)

	if not redis_conn.get(key):
		
		api = ph_api[conduit_gateway or 'default']

		ph = Phabricator(host=api['url'], token=api['token'])

		task = ph.maniphest.createtask(
			title=title,
			description=description,
			ownerPHID=api.get('owner') or maniphest.get('owner'),
			viewPolicy=maniphest['viewPolicy'],
			editPolicy=maniphest['editPolicy'],
			projectPHIDs=[maniphest['project']]
		)

		# <Result: {
			#'id': '4331', 
			#'phid': 'PHID-TASK-myofuodmwwca266qrgaj',
			#'authorPHID': 'PHID-USER-dylescmxfosc3u4qmc7c',
			#'ownerPHID': None,
			#'ccPHIDs': ['PHID-USER-dylescmxfosc3u4qmc7c'],
			#'status': 'open',
			#'statusName': 'Open',
			#'isClosed': False,
			#'priority': 'Normal',
			#'priorityColor': 'orange',
			#'title': 'HTTP500: parafie.wre.pl:8000/',
			#'description': '...Bug hash: ``HTTP50x-Ph-`',
			#'projectPHIDs': ['PHID-PROJ-kjcsoux56jqgupqly4ao'],
			#'uri': 'http://phabricator.tru.pl/T4331',
			#'auxiliary': [],
			#'objectName': 'T4331',
			#'dateCreated': '1522223793',
			#'dateModified': '1522223793',
			#'dependsOnTaskPHIDs': []
		#}>

		log.warn("Phabricator task created: {} {}".format(task['objectName'], task['uri']))
		created = datetime.datetime.now()
		with redis_conn.pipeline() as pipe:
			pipe.set(key, json.dumps({"task": task['objectName'], "created": converters.datetime2json(created)}))
			pipe.expire(key, ttl)
			pipe.execute()


def ReportBug(title, ex, traceback, config=None, request=None, conduit_gateway=None):

	endpoint_hash = Hash32(traceback)
	description = FormatDescription(endpoint_hash, traceback, config=config, request=request)
	return ReportToPhabricator(endpoint_hash, title, description, conduit_gateway=conduit_gateway)


def PhabricatorSink(get_response):

	@CatchExceptions
	def process_request(request):

		response = get_response(request)

		if not settings.DEBUG and response.status_code >= 500 and response.status_code <= 599 and not hasattr(response, "skip_bug_report"):

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

