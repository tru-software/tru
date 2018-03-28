
import os
import settings
import json
import datetime
import logging
import redis
import socket
import pprint

from phabricator import Phabricator

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

def ReportBug(title, request, traceback, config=None):

	if not POOL:
		log.error("PhabricatorSink: ReportBug: redis is not initialized")
		return False

	current_endpoint = getattr(request, 'CURRENT_ENDPOINT', None)
	# print(response._exc_details)
	if traceback:
		endpoint_hash = Hash32(traceback)
		name = list(i for i in traceback.split('\n') if i.strip())[-1]
	else:
		endpoint_hash = Hash32(current_endpoint or request.full_url)
		name = request.full_url

	key = redis_master_key.format(endpoint_hash)

	redis_conn = redis.Redis(connection_pool=POOL)

	if not redis_conn.get(key):

		environ = request.environ
		profile = request._cached_profile if hasattr(request, '_cached_profile') else None
		META = request.META

		r = 'URL: {}\nMETHOD: {}\nUSER_AGENT: {}\nUSER: {}\nREMOTE_ADDR: {}\nCURRENT_ENDPOINT: {}\n'.format(
			request.full_url,
			request.method,
			META.get('HTTP_USER_AGENT', 'NONE'),
			profile,
			META.get('REMOTE_ADDR', 'NONE'),
			current_endpoint
		)

		p = 'PID: {} ({})\nHOST: {}\n'.format(os.getpid(), settings.SERVER_ID, hostname)

		description = "Process:\n```{}```\n".format(p)
		description += "\n\nRequest:\n```{}```\n".format(r)
		if traceback:
			description += "\n\nTraceback:\n```{}```".format(traceback)

		if config:
			description += "\n\nConfig:\n```{}```".format(pprint.pformat(config))

		description += "\n\nMETA:\n```{}```".format(pprint.pformat(META))
		if request.POST:
			description += "\n\nPOST:\n```{}```".format(pprint.pformat(request.POST))
		if request.COOKIES:
			description += "\n\nCOOKIES:\n```{}```".format(pprint.pformat(request.COOKIES))
		description += "\n\nBug hash: `{}`".format(key)

		ph = Phabricator(host=ph_api['url'], token=ph_api['token'])

		task = ph.maniphest.createtask(
			title=title + name,
			description=description,
			ownerPHID=maniphest['owner'],
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


def PhabricatorSink(get_response):

	@CatchExceptions
	def process_request(request):

		response = get_response(request)

		if response.status_code >= 500 and response.status_code <= 599:

			try:
				if hasattr(response, '_exc_details'):
					exc, traceback = response._exc_details
				else:
					traceback = None
				ReportBug("HTTP{}: ".format(response.status_code), request, traceback)
			except Exception as ex:
				logging.exception("Cannot report bug")

		return response

	return process_request

