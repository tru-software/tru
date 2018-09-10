# -*- coding: utf-8 -*-
######################################################################
##                                                                  ##
##             Copyright (c) 2011, Tomasz Hławiczka                 ##
##                       All Rights Reserved.                       ##
##                                                                  ##
##             http://www.tru.pl                                    ##
##                                                                  ##
######################################################################

import logging
import settings
import os
import sys
import types
import copy
import datetime
import json

from django.http import Http404, HttpResponseRedirect, HttpResponseForbidden, HttpResponseNotModified
from mako import filters

from .mgr   import WebMgr
from .route import IRoute
from .view  import IView, ViewResponse
from .attr  import WebAttr
from ..WebExceptions import *

from tru.utils.backtrace import GetTraceback
from tru.dj.responses import NoCacheHttpResponse

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------

class ApplicationMeta(type):

	def __new__(cls, name, bases, d):
		new_class = type.__new__(cls, name, bases, d)

		new_class._register( new_class )
		return new_class

# ----------------------------------------------------------------------------

class Application(object, metaclass=ApplicationMeta):

	_instance       = None

	# ----------------------------------------------------------------------------

	def __new__(type):
		if not type._instance:
			type._instance = object.__new__(type)

		return type._instance

	# ----------------------------------------------------------------------------

	def __str__(self):
		return self.__class__.__name__

	# ----------------------------------------------------------------------------

	@staticmethod
	def _register(new_class):
		if not new_class.__name__ in ('Application', 'WebApplication', 'AdminApplication'):
			WebMgr.register(new_class)

	# ----------------------------------------------------------------------------

	def class_path(self):
		return "%s.%s"%(self.__module__,self.__class__.__name__)

	# ----------------------------------------------------------------------------

	def AjaxExceptionHandler(self, request, ex):
		if settings.DEBUG:
			return NoCacheHttpResponse( """%s<br/>Internal error: DEBUG: <b>%s</b><br/>
				<a href="#" onclick="$(this).parent().load('/webapi', %s); return false;">Try again!</a>""" %
				( request.CURRENT_TIME.strftime('%Y-%m-%d %H:%M:%S'), filters.html_escape(str(ex)), filters.html_escape(json.dumps(request.POST) )) )
		return NoCacheHttpResponse('Internal error!')

	# ----------------------------------------------------------------------------

	def _find_action(self, request, action_name):

		func = getattr(self, action_name, None)

		if func is None: # not isinstance(func, types.MethodType):
			log.error("Cannot find %r method (pointed by routes) in ctrl class %r for handling response", action_name, self )
			raise NotImplementedError('Action %r is not implemented' % action_name)

		return func

	# ----------------------------------------------------------------------------

	_default_json_error = {'error': 'Usługa jest chwilowo niedostępna. Prosimy spróbować później.', 'type': 'Internal'}

	def _execute_action(self, request, func):

		request.app['AppBody'] = func

		if getattr(func, '_attr_ajax', False) == 'json':
			status = 200
			try:
				r = func(request)
			except ResponseException as response:
				r = response.response
			except WebException as ex:
				r = ex.serialize()
			except Exception as ex:
				log.error("Requesting webapi-json function '%s' failed: \n%s\nException: %s\n\n", func, GetTraceback(), str(ex))
				r = self._default_json_error
				status = 503

			response = NoCacheHttpResponse(json.dumps(r).encode('utf-8'), content_type='application/json; charset=UTF-8')
			response.status_code = status
			return response

		try:
			r = func(request)
		except ViewResponse as view:
			r = view
		except ResponseException as response:
			r = response.response

		if isinstance(r, IRoute):
			return HttpResponseRedirect(r())

		return r

	# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------

class FakeWebRequest(object):

	def __init__(self, request=None):
		self.GET = {}
		self.POST = {}
		self.COOKIES = {}
		self.profile = None
		self.LANGUAGE_CODE = 'pl'
		# self.current_ucr = RouteManager().default()
		self.app = {}
		self.CURRENT_TIME = datetime.datetime.now()
		self.IsBot = False
		self.force_service = True

# ----------------------------------------------------------------------------
