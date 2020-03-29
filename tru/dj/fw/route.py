####################################################################
#                                                                  #
#             Copyright (c) 2011, Tomasz Hławiczka                 #
#                       All Rights Reserved.                       #
#                                                                  #
#             http://www.tru.pl                                    #
#                                                                  #
####################################################################

import copy
import logging
import settings

from .mgr import WebMgr
from routes import Mapper, request_config
from tru.utils.backtrace import GetClassPath
from tru.dj.responses import FileInMemory

log = logging.getLogger(__name__)


class IRoute(object):
	def build(self, name, parent):
		self._name = name
		self._order = 0
		return None

	def name(self):
		return self._name

	def generate(self, request, ABS_URL=False, **kwargs):

		route_name = self._component.__class__.__name__ + "." + self._name

		real_route = WebMgr._routes._routenames.get(route_name)
		path = WebMgr._routes.generate(real_route, **kwargs) or ''

		# print route_name, real_route, kwargs, WebMgr._routes.generate(real_route, **kwargs)

		if ABS_URL is True:
			return settings.BASE_URL + path
		return path

	def build(self, member_name, comp):
		pass

	def GetApplication(self, request):
		return None

	def GetMethod(self, request):
		return None


class Route(IRoute):
	def __init__(self, url, **route_params):
		self._url = url
		self._route_params = {}
		self._adapters = {}
		self._name = None
		self._component = None
		self._action_name = None
		self._more_args = ()
		self._more_kwargs = {}
		self._order = 0
		self._requirements = route_params.pop('requirements', None) or {}

		for k, v in list(route_params.items()):
			if callable(v):
				self._adapters[k] = v
			else:
				self._route_params[k] = v

	def Order(self, order_id):
		self._order = order_id
		return self

	def build(self, name, parent):
		self._name = parent.__class__.__name__ + "." + name
		self._component = parent
		self._action_name = self._route_params.pop('action', name)

	def GetApplication(self, request):
		return self._component

	def GetMethod(self, request):
		return self._action_name

	def clean(self):
		self._url = None
		self._route_params = None
		self._name = None
		self._component = None
		self._action_name = None
		self._more_args = None
		self._more_kwargs = None
		self._adapters = None
		self._requirements = None

	def clone(self, *args, **kwargs):
		new = Route(self._url, **self._route_params)
		new._name = self._name
		new._component = self._component
		new._action_name = self._action_name
		new._more_args = args + self._more_args
		new._more_kwargs = kwargs
		new._more_kwargs.update(self._more_kwargs)
		new._adapters.update(self._adapters)
		return new

	def __str__(self):
		return "Route: %s %s('%s')" % (
			GetClassPath(self._component.__class__),
			self._action_name,
			self._url
		)

	def name(self):
		return self._name

	# def merge(self, ucr):
	# 	n = self.clone()
	# 	n._prev = ucr
	# 	return n;

	# def extract(self):
	# 	return self._prev or URLCaller.default()

	def __call__(self, *args, **kwargs):

		request = WebMgr.Local.request
		ABS_URL = getattr(request, 'ABS_URL', None)

		if self._more_args:
			args = self._more_args + args

		r_kwargs = copy.copy(self._route_params)
		r_kwargs.update(self._more_kwargs)

		for k, v in list(kwargs.items()):
			if k in self._adapters:
				for k2, v2 in list(self._adapters[k](v).items()):
					r_kwargs[k2] = v2
			else:
				r_kwargs[k] = v

		for a in args:
			if hasattr(a, 'RoutesAdapter'):
				a.RoutesAdapter(r_kwargs, request, self)
			else:
				log.error("Used unlabeled argument '%s' for %s" % (a, self))

		if '__force_url' in r_kwargs:
			return r_kwargs['__force_url']

		anchor = ''
		if r_kwargs.get('anchor', None) is not None:
			anchor = '#' + r_kwargs.pop('anchor')

		if 'ABS_URL' in r_kwargs:
			ABS_URL = r_kwargs.pop('ABS_URL')

		# for k,v in r_kwargs.items():
		# 	if type(v) is unicode:
		# 		r_kwargs[k] = v

		r_kwargs['action'] = self._action_name
		r_kwargs['controller'] = self._component.__class__.__name__
		return self.generate(request, ABS_URL, **r_kwargs) + anchor


class StaticRoute(Route):

	def __init__(self, url, local_path, binary=False):
		super(StaticRoute, self).__init__(url)
		self._url = '/' + url.strip('/')
		self.content = FileInMemory(path=local_path, always_send=True, binary=binary)

	def __call__(self):
		return self._url

	def Execute(self, request):
		return self.content.Response(request)


class DirRoute(Route):

	def __init__(self, url, local_path):
		super(DirRoute, self).__init__(url.rstrip('/') + '/{path_info:.*}')
		self._base_url = '/' + url.strip('/')
		self._local_path = local_path.rstrip('/')

	def __call__(self):
		return self._url

	def Execute(self, request):
		from django.views.static import serve

		if not request.environ.get('PATH_INFO', None):
			return None

		full_path = request.environ['PATH_INFO']
		if not full_path.startswith(self._base_url + '/'):
			return None

		path = full_path[len(self._base_url) + 1:]

		return serve(request, path=path, document_root=self._local_path)
