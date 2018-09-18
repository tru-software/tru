# -*- coding: utf-8 -*-

import os
import sys
import re
import datetime
import time
import logging
import socket

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, Http404
from django.core import exceptions

from psycopg2._psycopg import OperationalError
from django.db.utils import OperationalError as DjangoOperationalError

from .. import HttpRequest
from ..responses import FileInMemory
from ..WebExceptions import TooLongRequestException, WebException, BotRequestException
from ...utils.backtrace import GetTraceback, FormatTraceback

log = logging.getLogger(__name__)
log_res = logging.getLogger('Resources')

hostname = socket.gethostname()

try:
	import version
	version_number, version_svn_rev = version.number, version.svn_rev
except ImportError:
	version_number, version_svn_rev = 0, 0


def GetEnvInfo(request=None):
	r = '';
	r += 'PID: {} ({})\nHOST: {}\nVERSION: {} (svn: {})\n'.format(os.getpid(), settings.SERVER_ID, hostname, version_number, version_svn_rev)

	if request is not None:
		environ = request.environ if hasattr(request, 'environ') else {}
		profile = request._cached_profile if hasattr(request, '_cached_profile') else None
		META = request.META if hasattr(request, 'META') else {}
		COOKIES = request.COOKIES if hasattr(request, 'COOKIES') else {}

		r += 'URL: %s\nUSER_AGENT: %s\nUSER: %s\nREMOTE_ADDR: %s\nCURRENT_ENDPOINT: %s\nMETHOD: %s\nCOOKIES: %s\n' % (
			request.full_url,
			META.get('HTTP_USER_AGENT', 'NONE'),
			profile,
			META.get('REMOTE_ADDR', 'NONE'),
			getattr(request, 'CURRENT_ENDPOINT', None),
			getattr(request, 'method', None),
			COOKIES
		)

	return r


# TODO: Override django.core.handlers.exception.response_for_exception
class CatchExceptions:

	templates_path = settings.BASE_DIR_FRONTEND + '/static/http/'

	_cache = {}

	def __init__(self, func):
		self.func = func

		self._page403 = self._load('403.html', status=403)  # HttpResponseForbidden
		self._page404 = self._load('404.html', status=404)  # HttpResponseNotFound
		self._page500 = self._load('500.html', status=500)  # HttpResponseServerError
		self._page502 = self._load('502.html', status=502)  # HttpResponseServerError
		self._page503 = self._load('503.html', status=503)  # HttpResponseServiceUnavailable


	def _load(self, filename, status):

		path = os.path.join(self.templates_path, filename)
		try:
			return self._cache[path]
		except KeyError:
			self._cache[path] = FileInMemory(path=path, always_send=True, status=status)
			return self._cache[path]


	def GetLogger(self, request):
		return request and hasattr(request, 'current_service') and request.current_service and request.current_service.GetLogger() or log


	def __call__(self, request):
		try:
			return self.func(request)
		except Http404 as e:

			if settings.DEBUG:
				self.GetLogger(request).exception(GetEnvInfo(request))
				from django.views import debug
				response = debug.technical_404_response(request, e)
			else:
				response = self._page404(request)

			response.source_exc = e
			return response

		except TooLongRequestException as ex:
			traceback = FormatTraceback()
			log_res.exception("TooLongRequestException: ('{}';  '{}'; '{}')".format(
				request.META['REMOTE_ADDR'],
				request.full_url,
				request.META.get('HTTP_USER_AGENT', 'NONE'),
				)
			)

			if settings.DEBUG:
				from django.views import debug
				return debug.technical_500_response(request, *sys.exc_info())

			response = self._page500(request, status=503)
			response._exc_details = (ex, traceback)
			return response

		except (OperationalError, DjangoOperationalError) as ex:

			traceback = FormatTraceback()
			log_res.exception("OperationalError: ('{}';  '{}'; '{}')".format(
				request.META['REMOTE_ADDR'],
				request.full_url,
				request.META.get('HTTP_USER_AGENT', 'NONE'),
				)
			)

			if settings.DEBUG:
				from django.views import debug
				return debug.technical_500_response(request, *sys.exc_info())

			response = self._page500(request, status=503)
			response._exc_details = (ex, traceback)
			response.skip_bug_report = True
			return response

		except exceptions.PermissionDenied as pd:
			if settings.DEBUG:
				self.GetLogger(request).exception(GetEnvInfo(request))
			response = self._page403(request)
			response.source_exc = pd
			return response

		except BotRequestException as ex:
			self.GetLogger(request).exception(GetEnvInfo(request))
			response = self._page503(request, status=503)
			response.skip_bug_report = True
			return response
			
		except NotImplementedError as ex:
			self.GetLogger(request).exception(GetEnvInfo(request))
			return self._page500(request, status=503)

		except SystemExit:
			pass # See http://code.djangoproject.com/ticket/1023

		except Exception as ex:  # Handle everything else

			traceback = FormatTraceback()
			self.GetLogger(request).exception(GetEnvInfo(request))

			#if settings.DEBUG:
				#from django.views import debug
				#return debug.technical_500_response(request, *sys.exc_info())

			response = self._page502(request)
			response._exc_details = (ex, traceback)

			return response


# ----------------------------------------------------------------------------
