# -*- coding: utf-8 -*-

import logging
import settings
import itertools
import time
import types
import copy
import sys
import json
from threading import local

from routes import Mapper, request_config
from django.http import Http404, HttpResponseRedirect, HttpResponse

log = logging.getLogger(__name__)


class ActionWrapper(object):

	def __init__(self, obj, func, name):

		from .route import Route

		self.obj = obj
		self.route = None
		self.name = name

		if isinstance(func, types.MethodType):
			self.func = func
			if self.func._attr_public:
				if hasattr(self.func, "_attr_route"):
					self.route = self.func._attr_route
				elif hasattr(self.func, "_attr_ajax"):
					self.route = Route( '/webapi/{}/{}'.format( obj.__class__.__name__, name) )
			self.proc = self.func
		elif isinstance(func, Route):
			self.func = func
			self.route = func
			self.proc = func.Execute

	def __call__(self, *args, **kwargs):
		return self.proc(*args, **kwargs)

	def __getattr__(self, name):
		return getattr(self.func, name)
		# return self.__class__(new_func)

	def PostAddr(self):
		return self.Link()

	def Link(self, *args, **kwargs):
		if self.route is None:
			return None
		return self.route(*args, **kwargs)

	def Redirect(self, *args, **kwargs):
		return HttpResponseRedirect( self.route(*args, **kwargs) )

	def RedirectWithJavaScript(self, *args, **kwargs):
		from .exceptions import RedirectWithJavaScriptResponse
		return RedirectWithJavaScriptResponse( self.route(*args, **kwargs) )

# ----------------------------------------------------------------------------

class ThreadSafeData(local):

	def __init__(self):
		self.request = None
		self.queries_counter = 0
		self.queries_timer = 0.0
		self.redis_counter = 0
		self.redis_timer = 0.0
		self.sql_trace = False

	def OnDBCall(self, cnt, tm):
		self.queries_counter += cnt
		self.queries_timer += tm

# ----------------------------------------------------------------------------

class WebManagerClass(object):

	_instance = None

	# ----------------------------------------------------------------------------

	def __new__(type):
		if not WebManagerClass._instance:
			WebManagerClass._instance = object.__new__(type)
			self = WebManagerClass._instance
			self.WebAppsByPaths = {}  # klasy komponentów (WebApplication + WebPart) class_path => object
			self.WebAppsByNames = {}  # klasy komponentów (WebApplication) class_name => object
			self.Local = ThreadSafeData()
			self._routes = Mapper()
			self._all_routes = {}  # route name (application.public_id+"."+route_name) => route object
			self.InternalData = {}

		return WebManagerClass._instance

	# ----------------------------------------------------------------------------

	def register(self, comp_class):

		import utils as utils
		from .route import Route

		obj = comp_class()
		class_path = utils.GetClassPath(comp_class)
		self.WebAppsByPaths[ class_path ] = obj
		self.WebAppsByNames[ comp_class.__name__ ] = obj

		for name, func in list(comp_class.__dict__.items()):

			if isinstance(func, types.FunctionType):
				if getattr(func, '_attr_public', False) != True:
					continue
				wrapper = ActionWrapper( obj, getattr(obj, name), name )
				setattr(obj, name, wrapper)
			elif isinstance(func, Route):
				wrapper = ActionWrapper( obj, getattr(obj, name), name )
				setattr(obj, name, wrapper)

	# ----------------------------------------------------------------------------

	def build_views(self):
		from .view import IView

		for comp_class in list(self.WebAppsByPaths.values()):
			meta_class = comp_class.__class__.__dict__.get("Views",None)
			if meta_class:
				for member_name in meta_class.__dict__:
					member = meta_class.__dict__[member_name]
					if isinstance( member, IView ):
						member.build( member_name, comp_class )

	# ----------------------------------------------------------------------------

	def build_routes(self):

		all_routes=[]

		for comp in list(self.WebAppsByPaths.values()):
			comp._sorted_routes = []
			for member_name in comp.__dict__:
				member = getattr(comp, member_name)
				if isinstance( member, ActionWrapper ) and member.route:
					member.route.build( member_name, comp )
					comp._sorted_routes.append( member.route )
			comp._sorted_routes.sort( key=lambda r: r._order )

			all_routes.extend(comp._sorted_routes)

		all_routes.sort( key=lambda r: r._order )

		list(map( self.append_route, all_routes ))

	# ----------------------------------------------------------------------------

	def append_route(self, route):

		self._all_routes[ route._component.__class__.__name__ + "." + route._name ] = route

		self._routes.connect (
			route._component.__class__.__name__ + "." + route._name, #route._name,
			route._url,
			controller=route._component.__class__.__name__,
			action=route._action_name,
			requirements=route._requirements,
			**route._route_params
		)

	# ----------------------------------------------------------------------------

	def FindRoute(self, request):

		config = request_config()
		config.mapper = self._routes
		# route matching
		# -- Assignment of environ to config triggers route matching
		config.environ = request.environ

		if config.mapper_dict is None:
			# log.error( u"Cannot find route for: '%s'" % ( request.environ.get('PATH_INFO', '<unset PATH_INFO>') ) );
			return None

		# request.environ['pylons.routes_dict'] = request.ROUTE
		# request.environ['wsgiorg.routing_args'] = ((), match)
		request.environ['routes.route'] = config.route
		return config

	# ----------------------------------------------------------------------------

	def GetCurrentRoute(self, request, route_name, url_params ):

		routes_names = [x for x,y in list(self._routes._routenames.items()) if y == route_name]
		if len(routes_names) > 0:
			try:
				route = self._all_routes.get(routes_names[0], None)
				if route:
					all_args = {}
					for x,y in list(request.GET.items()):
						all_args[ str(x) ] = y
					for x,y in list(url_params.items()):
						all_args[ str(x) ] = y
					all_args.pop( 'controller', None )
					all_args.pop( 'action', None )
					return route, route.clone( **all_args )
			except Exception as ex:
				if settings.DEBUG:
					raise
				log.error('Cannot create current_ucr: %s' % ex.message )
		return None, None

	# ----------------------------------------------------------------------------

	def get(self, class_name):
		obj = self.WebAppsByPaths.get( class_name, None )
		return obj

	# ----------------------------------------------------------------------------

	def StartRequest(self, request):
		self.Local.request = request
		self.Local.queries_counter = 0
		self.Local.queries_timer = 0.0

	# ----------------------------------------------------------------------------

	def FinishRequest(self, request):
		self.Local.request = None

	# ----------------------------------------------------------------------------


WebMgr = WebManagerClass()
