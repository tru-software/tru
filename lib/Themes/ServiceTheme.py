# -*- coding: utf-8 -*-

from pathlib import Path
from django.conf import settings
import logging
import os
import imp
import zlib
import json

from tru.fs import stamp as filestamp
from tru.dj.responses import FileInMemory
from tru.io.html2html import cleanup_xhtml

from bs4 import BeautifulSoup

log = logging.getLogger(__file__)


class ServiceTheme:

	PROPS = {
		'Name'                 : None,
	}

	DEBUG = settings.DEBUG
	BASE_DIR_FRONTEND = Path(settings.BASE_DIR_FRONTEND)

	def __init__(self, id, path, url, mod):
		self.id = id
		self.path = Path(path)
		self.url = url
		self._theme_dir_name = id
		self.script_url = None
		self.script_crc32 = None

		favicon = getattr(mod, 'favicon', None)
		if favicon:
			self.favicon_url = os.path.join(self.url, favicon)
			self.favicon_path = self.path / favicon
		else:
			self.favicon_url = self.url + '/favicon.ico'
			self.favicon_path = self.path + '/favicon.ico'

		if not os.path.isfile(self.favicon_path):
			raise IOError(f'File "{self.favicon_path}" is missing')


		self.style = getattr(mod, 'style', None) or 'service.css'
		self.script = None

		self.ImportProps(mod)

		self.favicon = FileInMemory(path=str(self.favicon_path), binary=True)
		self.favicon_url += "?v={}".format(self.favicon.GetCRC())

		if not self.DEBUG:
			self.style = self.style.replace('.css', '.min.css')
			if self.script:
				self.script = self.script.replace('.js', '.min.js')

		self.style_url = filestamp.Mark(self.style, dir=str(self.path), netloc=self.url, debug=self.DEBUG)
		if self.script:
			self.script_url = filestamp.Mark(self.script, dir=str(self.path), netloc=self.url, debug=self.DEBUG)

		self._touchicons_code = ''
		self._touchicons_files = {} # dict: '57x57' (attr "sizes") => '/static/themes/../apple-touch-icon-precomposed.png' (attr "href")
		self.theme_script_url = ''
		self.theme_css_url = ''

		touchicons = self.path / 'touch-icons.html'
		if os.path.isfile(touchicons):
			with open(touchicons, 'r') as f:
				self._touchicons_code = cleanup_xhtml(f.read(), strip_comments=True).strip().replace('\n\n', '\n')
				soup = BeautifulSoup(self._touchicons_code, 'lxml')
				for tag in soup.findAll('link', href=True):
					if tag.get('rel') == 'apple-touch-icon-precomposed':
						sizes = tag.get('sizes') or '57×57'
						self._touchicons_files[sizes] = tag.get('href')

		self.theme_css_url = filestamp.Mark(('service.css' if self.DEBUG else 'service.min.css'), dir=str(self.path), netloc=self.url, debug=self.DEBUG)

		theme_script_url = 'script.js' if self.DEBUG else 'script.min.js'
		if os.path.isfile(os.path.join(self.path, theme_script_url)):
			self.theme_script_url = filestamp.Mark(theme_script_url, dir=str(self.path), netloc=self.url, debug=self.DEBUG)

		self.OnLoadTheme(mod)

	def ImportProps(self, mod):
		for k,v in list(self.PROPS.items()):
			setattr(self, k, getattr(mod, k, v))

	def OnLoadTheme(self, mod):
		pass

	@staticmethod
	def _crc32(filepath):
		try:
			with open(filepath, 'r') as f:
				return '%x' % int(zlib.crc32(f.read()) & 0xFFFFFFFF)
		except IOError:
			pass
		return None

	def GetName(self):
		return self.Name or self._theme_dir_name

	def GetURL(self):
		return self.url

	def GetStyleURL(self):
		return self.style_url

	def GetScriptURL(self):
		return self.script_url

	def GetScreenshotURL(self):
		return self.screenshot_url

	def GetFaviconURL(self):
		return self.favicon_url

	def GetFaviconDir(self):
		return self.favicon_path

	def GetFavicon(self):
		return self.favicon

	def GetTouchIconsCode(self):
		return self._touchicons_code

	def GetAppleTouchIcon(self, size='180x180'):
		return self._touchicons_files.get(size)

	def GetThemeFile(self, filepath):
		if not self.url:
			return filepath
		return self.url + '/' + filepath.lstrip('/')

	def GetThemeCSSURL(self, request):
		return self.theme_css_url

	def GetThemeScriptURL(self, request):
		return self.theme_script_url

	
	def __str__(self):
		return '{}("{}")'.format(self.__class__.__name__, self.path)

# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------

class ServiceThemeMgrClass(object):

	themes = {}
	themes_by_url = {}
	default = None
	_themes_list_desktop = []
	_themes_list_mobile = []

	def GetDefault(self):
		return self.default

	def FindTheme(self, theme_id, default=True):
		return self.themes.get(theme_id, self.default if default else None)

	def FindByURL(self, theme_path, default=True):
		return self.themes_by_url.get(theme_path, self.default if default else None)

	def GetDefaultTheme(self):
		return self.default

	def Load(self, basedirs):

		self._themes_list_desktop = []
		self._themes_list_mobile = []
		for themes_dir, themes_url in basedirs:

			for theme_dir in os.listdir(themes_dir):
				theme_path = os.path.join(themes_dir,theme_dir)
				theme_url = themes_url+'/'+theme_dir
				if not os.path.isdir(theme_path) or not os.path.isfile(os.path.join(theme_path, '__init__.py' )):
					continue

				mod = imp.load_source('service_theme_%s' % (theme_dir,), os.path.join(theme_path, '__init__.py' ))

				theme = ServiceTheme(theme_dir, theme_path, theme_url, mod)
				self.themes[theme_dir] = theme
				self.themes_by_url[theme_url] = theme


		self.default = self.themes.get('default')

		self._themes_list_desktop.sort()
		self._themes_list_mobile.sort()

	def GetThemes(self, allow_limited=False):
		collection = list(self.themes.values()) if allow_limited else [ i for i in list(self.themes.values()) if not i.is_limited ]
		return sorted( collection, key=lambda theme: theme.name )

	def GetThemesList(self, desktop=False, mobile=False):
		if desktop:
			return self._themes_list_desktop
		if mobile:
			return self._themes_list_mobile
		return []
