# -*- coding: utf-8 -*-

import os
import copy
import logging
import settings
import datetime
import json

from mako.lookup import TemplateLookup
from mako import runtime as mako_runtime, filters, util as mako_util

from .mgr   import WebMgr

from django.http import HttpResponse
# from django.core.hanlders import WSGIRequest

from tru.io import html_helpers
from django.utils.translation import ugettext


log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------

class IView:
	def build(self):
		pass

	def __call__(self, env={}, proc=None):
		pass

# ----------------------------------------------------------------------------

class WebAppsHelperClass:

	def __getattr__(self, name):

		if name in WebMgr.WebAppsByNames:
			return WebMgr.WebAppsByNames[name]
		raise AttributeError(name)

WebAppsHelper = WebAppsHelperClass()

# ----------------------------------------------------------------------------

class ViewResponse(HttpResponse, BaseException):

	def __init__(self, view, request=None, env=None, proc=None):

		super(ViewResponse, self).__init__(content_type='text/html')

		self.view = view
		self.env = env
		self.proc = proc
		self.request = request

		if proc is None and request is not None:
			self.__render_view()

	def __call__(self, request, env=None):
		self.env = env or self.env or {}
		self.request = request # need to be WSGIRequest or FW.FakeRequest
		self.__render_view()
		return self

	def __render_view(self):
		self.content = self.view._render_context(self.request, self.env, self.proc)

# ----------------------------------------------------------------------------

class MakoView(IView):

	def __init__(self, filename, dirs):
		self.__mako_filename         = filename
		self.__mako_template         = None
		self.__mako_lookup           = None
		self.__dirs                  = dirs or settings.MAKO_TEMPLATE_DIRS

		self.build()

	# ----------------------------------------------------------------------------

	def __build(self):

		self.__mako_lookup = TemplateLookup(
			directories         = self.__dirs,
			filesystem_checks   = settings.MAKO_ALWAYS_RELOAD,
			input_encoding      = 'utf-8',
			output_encoding     = 'unicode',
			disable_unicode     = False,
			cache_enabled       = False, # not ( settings.DEBUG or settings.MAKO_ALWAYS_RELOAD ),
			modulename_callable = MakoView.default_module_name if settings.DEBUG or settings.SERVER_DEV else None,
			default_filters     = []
		)

	# ----------------------------------------------------------------------------

	def build(self, name=None, dirs=None):
		if dirs:
			self.__dirs = dirs
		self.__build()
		self.load_template()

	# ----------------------------------------------------------------------------

	def load_template(self):
		if not self.__mako_template or settings.MAKO_ALWAYS_RELOAD:
			if not self.__mako_lookup:
				self.__build()
			# To załaduje sam plik mako
			try:
				self.__mako_template = self.__mako_lookup.get_template( self.__mako_filename )
				# natomiast trzeba jeszcze załadować nadrzędne mako
				tmp_context = mako_runtime.Context(mako_util.FastEncodingBuffer())
				tmp_context._with_template = self.__mako_template
				mako_runtime._populate_self_namespace(tmp_context, self.__mako_template)
			except Exception as ex:
				log.error( "Cannot load template: %s (%s) in %s: %s" % (
					self.__mako_filename,
					self.__mako_template.module if self.__mako_template else 'file not found',
					self.__mako_lookup.directories,
					ex
				))
				# print "Cannot load template: %s (%s)" % (self.__mako_filename, self.__mako_template.module if self.__mako_template else 'file not found')
				raise

	# ----------------------------------------------------------------------------

	def __call__(self, request, env={}, proc=None):
		return ViewResponse( self, request, env, proc )

	# ----------------------------------------------------------------------------

	def __getattr__(self, name):

		if hasattr(self.__mako_template.module, 'render_%s'%name):
			return ViewResponse(self, proc=name)
		raise AttributeError(name)

	# ----------------------------------------------------------------------------

	#def render(self, context, env={}, proc_name=None ):

		#dictionary = env
		#request = context.get('request')
		#dictionary['request'] = request

		#self._build_std_env(dictionary, context)
		#dictionary.update(env)

		#self.load_template()

		#template = self.__mako_template

		#local_context = context.clone(dictionary)
		#local_context._push_buffer()
		#local_context._with_template = template

		#templ = template if proc_name == None else template.get_def(proc_name)
		#templ.render_context(local_context)

		#content = local_context._pop_buffer().getvalue()
		#context.write( content )

	# ----------------------------------------------------------------------------

	def _render_context(self, request, env={}, proc_name=None):

		dictionary = copy.copy(env)
		if 'request' not in dictionary:
			dictionary['request'] = request

		self._build_std_env(dictionary, request=request)
		self.load_template()

		templ = self.__mako_template if proc_name is None else self.__mako_template.get_def(proc_name)

		return templ.render_unicode(**dictionary)

	# ----------------------------------------------------------------------------

	def _build_std_env(self, env, request, parent_context=None):

		env['py2js'] = lambda x: json.dumps(x)
		env['nl2br'] = lambda x: x.replace('\n', '<br/>').replace('\r', '\n')
		env['WebApps'] = WebAppsHelper
		env['_'] = ugettext
		env['HTML'] = html_helpers.HTMLHelpers

		# TODO:
		import datamodel
		import core
		env['DM'] = datamodel
		env['FW'] = core
		# env['LANG'] = request.LANGUAGE_CODE
		# env['render_time'] = lambda: str( datetime.datetime.now().time() )

	# ----------------------------------------------------------------------------

	@staticmethod
	def default_module_name(filename, uri):
		'''
		Will store module files in the same directory as the corresponding template files.
		detail about module_name_callable, go to 
		http://www.makotemplates.org/trac/ticket/14
		'''
		if not filename.startswith(settings.BASE_DIR):
			raise Exception("Mako-template '%s' is not in project directory: %s" % (filename, settings.BASE_DIR))

		return "%s/mako/%s.py" % (settings.TMP_DIR, filename[len(settings.BASE_DIR)+1:])

	# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------

class MakoDir(object):

	def __init__(self, module_name):
		self.module_path = list(self.__dir_of_class(module_name, settings.MAKO_TEMPLATE_DIRS))

	def MakoView(self, filename):
		return MakoView(filename, self.module_path)

	@staticmethod
	def __dir_of_class(module, roots):

		test = lambda x: x if os.path.isdir(x) else None
		if os.path.dirname(module):
			return module

		parts = module.split('.')

		for i in roots:
			yield i

			t = test(i + '/' + '/'.join(parts))
			if t:
				yield t
			t = test(i + '/' + '/'.join(parts[:-1]))
			if t:
				yield t

	# ----------------------------------------------------------------------------
