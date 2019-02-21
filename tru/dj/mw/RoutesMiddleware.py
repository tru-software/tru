import re
import logging
import settings
import json

from .CatchExceptions import CatchExceptions

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, HttpResponseServerError, Http404
from mako.filters import html_escape

import core as FW

log = logging.getLogger(__name__)
log_access = logging.getLogger('Access')

# ----------------------------------------------------------------------------

def FindRouteMiddleware(get_response):

	@CatchExceptions
	def process_request(request):

		request.ROUTE = {}
		config = FW.WebMgr.FindRoute(request)

		if not config:
			raise Http404("Brak route: {} '{}'".format(request.environ['REQUEST_METHOD'], request.full_url))

		match = config.mapper_dict
		"""
		for key, val in match.items():
			if val and isinstance(val, str):
				if isinstance(val, str):
					match[key] = str(val, 'UTF8')
				elif isinstance(val, str):
					match[key] = val
		"""

		request.ROUTE.update(match)

		request.original_route, request.current_route = FW.WebMgr.GetCurrentRoute(request, config.route, request.ROUTE)

		if not request.original_route or not request.current_route:
			raise Http404("Brak UCR: {} '{}'".format(request.environ['REQUEST_METHOD'], request.full_url))

		request.ROUTE.pop('controller', None)
		request.ROUTE.pop('action', None)

		if hasattr(request.original_route, 'Execute'):
			response = request.original_route.Execute(request)
			if response:
				ctrl_instance = request.original_route.GetApplication(request)
				method_name = request.original_route.GetMethod(request)
				func = ctrl_instance._find_action(request, method_name)
				request.ENDPOINT = '{}.{}'.format(func.__self__.__class__.__name__, func.__name__)

				return response

		return get_response(request)

	return process_request

# ----------------------------------------------------------------------------

def ExecuteRouteMiddleware(get_response):

	@CatchExceptions
	def process_request(request):

		ctrl_instance = request.original_route.GetApplication(request)
		method_name = request.original_route.GetMethod(request)
		func = ctrl_instance._find_action(request, method_name)
		request.ENDPOINT = '{}.{}'.format(func.__self__.__class__.__name__, func.__name__)

		if getattr(func, '_attr_public', False) is not True:
			# add following decorator to your function:
			# from service import *
			# @FW.WebAttr.public
			return HttpResponseForbidden('Requested method is NOT accessible.')

		if getattr(func, '_attr_login_required', False) is True and request.user is None:

			# login_app = FW.WebMgr.WebAppsByNames['Auth']
			# login_func = login_app.LoginPage

			# ctrl_instance = login_app
			# func = login_func

			if getattr(func, '_attr_ajax', False) == 'json':
				return HttpResponse(json.dumps({'error': {'msg': 'Zaloguj się', 'type': 'LoginRequired'}}), status=401)

			if getattr(func, '_attr_ajax', False) == 'html':
				return HttpResponse('<a href="{}">Zaloguj się</a>'.format(html_escape(FW.WebMgr.WebAppsByNames['MainPage'].Index.Link(login=request.full_url_protocol))), status=401)

			if request.method == 'GET':
				return HttpResponseRedirect(FW.WebMgr.WebAppsByNames['MainPage'].Index.Link(login=request.full_url_protocol))
			# elif request.method == 'POST':
			#	return FW.HttpResponseRedirect(FW.WebMgr.WebAppsByNames['MainPage'].Index.Link())
			return HttpResponse(status=401)

		# if request.user is None and getattr(func, '_attr_unlogged_required', False) != True:
		#	return FW.HttpResponseRedirect( FW.WebMgr.WebAppsByNames['Auth'].LoginPage.Link(url=request.current_route(ABS_URL=True)) )

		try:
			response = ctrl_instance._execute_action(request, func)
		except FW.ResponseException as response:
			response = response.response
		except FW.ViewResponse as ex:
			response = ex

		if getattr(func, 'suppress_access_log', False) is True:
			response.suppress_access_log = True

		return response

	return process_request
