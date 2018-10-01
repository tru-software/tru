import datetime
import time
import threading
import logging
from django.conf import settings


log404 = logging.getLogger('HTTP404')
log_access = logging.getLogger('Access')


local_data = threading.local()
local_data.request = None


def StoreCurrentRequestMiddleware(get_response):

	def process_request(request):

		try:
			request.CURRENT_TIME = datetime.datetime.now()
			local_data.request = request
			return get_response(request)
		finally:
			local_data.request = None

	return process_request


def GetCurrentRequest():
	return local_data.request


class Stats:
	
	class Cnt:
		__slots__ = ('cnt', 'tm')

		def __init__(self):
			self.cnt = 0
			self.tm = 0.0
		
		def Incr(self, cnt, tm):
			self.cnt += cnt
			self.tm += tm
		
		def Format(self, cls, fmt):
			return fmt.format(cls, self.cnt, self.tm)

	__slots__ = (
		'begin',
		#'pg',
		#'es',
		#'redis',
		#'mongo',
		#'cache',
	)

	def __init__(self):
		self.begin = time.time()

		#self.pg = Stats.Cnt()
		#self.es = Stats.Cnt()
		#self.redis = Stats.Cnt()
		#self.mongo = Stats.Cnt()
		#self.cache = Stats.Cnt()

	def GetParts(self, fmt_tm, fmt_call):

		yield fmt_tm.format(time.time() - self.begin)

		#if self.pg_cnt:
			#yield self.pg.Format('PG', fmt_call)
		#if self.es_cnt:
			#yield self.es.Format('ES', fmt_call)
		#if self.redis_cnt:
			#yield self.redis.Format('RD', fmt_call)
		#if self.mongo_cnt:
			#yield self.mongo.Format('MO', fmt_call)
		#if self.cache_cnt:
			#yield self.cache.Format('CH', fmt_call)


def AccessLogMiddleware(get_response):

	def process_request(request):

		response = None
		try:
			request.stats = AccessLogMiddleware.RequestStatsClass()
			response = get_response(request)
		finally:
			status = 'HTTP{}'.format(response.status_code) if response else 'Exception'

			if settings.DEBUG:
				stats = ' '.join(request.stats.GetParts('\033[90mT\033[0m=\033[91m{:.4f}\033[0m', '\033[90m{}\033[0m=\033[93m{}\033[0m/\033[91m{:.4f}\033[0m'))

				log_func = log_access.info
				if response.status_code >= 400:
					status = '\033[01m\033[41m\033[97m{}\033[0m'.format(status)
					log_func = log_access.error
				else:
					status = '\033[92m{}\033[0m'.format(status)

				log_func('\033[93m[%s\033[93m] \033[95m%s\033[0m \033[94m%s\033[0m %s' % (stats, request.method, request.full_url, status))
			elif getattr(response, 'suppress_access_log', False) is not True:

				stats = ' '.join(request.stats.GetParts('T={:.4f}', '{}={}/{:.4f}'))
				log_access.info('[%s] %s %s %s %s' % (stats, request.META['REMOTE_ADDR'], request.method, request.full_url, status))

			if response and response.status_code == 404:
				log404.error("%s ('%s'; '%s'; '%s')" % (getattr(response, 'error_msg', 'Unknown error'), request.META['REMOTE_ADDR'], request.full_url, request.META.get('HTTP_USER_AGENT', 'NONE')))

		return response

	return process_request

AccessLogMiddleware.RequestStatsClass = Stats
