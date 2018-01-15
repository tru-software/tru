# -*- coding: utf-8 -*-

import sys
import re
import datetime
import time
import settings
import logging

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, HttpResponseServerError, Http404
from django.core import exceptions
import core as FW

from tru.utils.backtrace import GetTraceback

log = logging.getLogger(__name__)
log404 = logging.getLogger('HTTP404')
log_access = logging.getLogger('Access')


def EnvironMiddleware(get_response):

	def process_request(request):
		# In case of fcgi configuration, the 'SCRIPT_NAME' need to be empty.
		# See routes url_for().
		# http://routes.groovie.org/generating.html#generating-urls-with-subdomains
		request.environ['SCRIPT_NAME'] = ''
		# ---
		request.CURRENT_TIME = datetime.datetime.now()
		request.app = {}

		try:
			FW.WebMgr.StartRequest(request)
			response = get_response(request)
			return response
		finally:
			FW.WebMgr.FinishRequest(request)

	return process_request

# ----------------------------------------------------------------------------

from tru.dj.responses import FileInMemory

def __load(filename):
	return FileInMemory(path=settings.BASE_DIR_FRONTEND + '/static/http/' + filename, always_send=True)

__page403 = __load('403.html')  # HttpResponseForbidden
__page404 = __load('404.html')  # HttpResponseNotFound
__page500 = __load('500.html')  # HttpResponseServerError
__page502 = __load('502.html')  # HttpResponseServerError

# ----------------------------------------------------------------------------

def CatchExceptions(func):

	def process_request(request):

		try:
			return func(request)
		except Http404 as ex:
			if settings.DEBUG:
				log.error("\n%s\n" % (GetTraceback()))
			response = HttpResponseNotFound(__page404.content)
			response.error_msg = str(ex)
			return response

		except exceptions.PermissionDenied as pd:
			log.error("%s\nPermissionDenied Exception: %s" % (GetTraceback(), pd.message))
			return HttpResponseForbidden(__page403.content)

		except Exception as ex: # Handle everything else
			log.error("Exception: ('%s';  '%s'; '%s'):\n\n%s\n\n%s" % (
				request.META['REMOTE_ADDR'],
				request.full_url,
				request.META.get('HTTP_USER_AGENT', 'NONE'),
				str(ex),
				GetTraceback())
			)

			if settings.DEBUG:
				from django.views import debug
				return debug.technical_500_response(request, *sys.exc_info())
			else:
				#mail_admins(subject, message, fail_silently=True)
				return HttpResponseServerError(__page500.content)

		except SystemExit:
			pass

	return process_request

# ----------------------------------------------------------------------------

def AccessLogMiddleware(get_response):

	def process_request(request):

		__begin = time.time()
		response = None
		try:
			response = get_response(request)
		finally:
			__end = time.time()
			endpoint = getattr(request, 'ENDPOINT', 'Unknown-endpoint')
			status = 'HTTP{}'.format(response.status_code) if response else 'Exception'
			if settings.DEBUG:
				stats = '[%.4f   \033[93m%5d\033[0m   %.4f]' % ( __end-__begin, FW.WebMgr.Local.queries_counter, FW.WebMgr.Local.queries_timer)
				log_access.info('%s \033[90m%s\033[0m %s \033[92m%s %s\033[0m [\033[94m%s\033[0m]' % (stats, request.META['REMOTE_ADDR'], request.method, request.full_url, status, endpoint))
			elif getattr(response, 'suppress_access_log', False) is not True:
				stats = '[%.4f   %5d   %.4f]' % (__end-__begin, FW.WebMgr.Local.queries_counter, FW.WebMgr.Local.queries_timer)
				log_access.info('%s %s %s %s %s [%s]' % (stats, request.META['REMOTE_ADDR'], request.method, request.full_url, status, endpoint))

			if response and response.status_code == 404:
				log404.error("%s ('%s'; '%s'; '%s')" % (getattr(response, 'error_msg', 'Unknown error'), request.META['REMOTE_ADDR'], request.full_url, request.META.get('HTTP_USER_AGENT', 'NONE')))

		return response

	return process_request
