import datetime
import logging

import settings


def CurrentDatetimeMiddleware:

	external_log = None

	def __init__(self, get_response):
		self.get_response = get_response
		self.log = self.external_log or logging.getLogger(__name__)

	def IsAllowed(self, request):
		return request.profile and request.profile.has_perm(self.Perms.ServicesTester)

	def __call__(self, request):

		cache_state = request.GET.get('cache', '1')

		if '__date__' in request.GET and self.IsAllowed(request):
			date = request.GET['__date__']
			if date.isdigit() or (date.startswith('-') and date[1:].isdigit()):
				date = (datetime.datetime.now() + datetime.timedelta(int(date)))
				cache_state = '0'
			elif '-' in date and len(date) == len('2016-07-02'):
				date = datetime.datetime(*list(map(int, date.split('-'))))
				cache_state = '0'
			elif '-' in date and len(date) == len('2016-07-02-12-26-45'):
				date = datetime.datetime(*list(map(int, date.split('-'))))
				cache_state = '0'
			else:
				date = datetime.datetime.now()

			request.CURRENT_TIME = date

		if cache_state == '0':
			request.app['RobotsNoIndex'] = True
			if FW.WebMgr.cache_manager and getattr(request, 'cache', None):
				FW.WebMgr.cache_manager.release_current_connection(request.cache.get_cache())

			request.cache = FakeCache()

		if request.IsBot:
			request.cache = BotsCache(request.cache)
		elif cache_state == '2':
			request.cache = WriteOnlyCache(request.cache)
			request.app['RobotsNoIndex'] = True

		return get_response(request)

	return process_request
