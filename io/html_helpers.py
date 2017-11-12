# -*- coding: utf-8 -*-
import inspect
import logging
import types
import warnings
import os
import re
import sys
import datetime
import urllib.request, urllib.parse, urllib.error

from mako import filters
from mako.filters import html_escape
from markupsafe import Markup

from . import converters

log = logging.getLogger(__name__)

class HTMLHelpers(object):

	WeekDay2PL = ( 'Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela' )
	Mth2PL  = ( '', 'Stycznia', 'Lutego', 'Marca', 'Kwietnia', 'Maja', 'Czerwca', 'Lipca', 'Sierpnia', 'Września', 'Października', 'Listopada', 'Grudnia' )
	Mth2PL2  = ( '', 'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień' )
	Mth2PL_lower = [ i.lower() for i in Mth2PL ]
	Mth2PL2_lower = [ i.lower() for i in Mth2PL2 ]

	@staticmethod
	def OptionSelected(cond):
		return Markup(cond and 'selected="selected"' or '')

	@staticmethod
	def Checked(cond):
		return Markup(cond and 'checked="checked"' or '')

	@staticmethod
	def Disabled(cond):
		return Markup(cond and 'disabled="disabled"' or '')

	@staticmethod
	def AsyncLoader():
		return Markup('(loading..) <img src="/static/images/loading.gif" />')

	@staticmethod
	def dict(**kwargs):
		return kwargs

	@staticmethod
	def option_selected(cond):
		return Markup(cond and 'selected="selected"' or '')

	@staticmethod
	def option(value, name=None, cond=False):
		if not isinstance(cond, bool):
			cond = str(cond) == value
		return Markup('<option value="{}"{}>{}</option>'.format(html_escape(value), ' selected="selected"' if cond else '', html_escape(name or value)), )

	@staticmethod
	def checked(cond):
		return Markup(cond and 'checked="checked"' or '')

	@staticmethod
	def disabled(cond):
		return Markup(cond and 'disabled="disabled"' or '')

	@staticmethod
	def async_loader():
		return Markup('(loading..) <img src="/static/images/loading.gif" />')

	@staticmethod
	def tag_params(params):
		if params is None:
			return ""
		s=""
		for (k,v) in list(params.items()):
			s="%s %s=\"%s\"" % (s, filters.html_escape(k), filters.html_escape(v))
		return s

	@staticmethod
	def date(date_field, ucr=None, params=None):
		if date_field is None:
			return ''
		if ucr:
			return ("<a %s %s>%s</a>") % (
				SimpleHtmlHelper.tag_params( {'href': ucr(date=date_field.strftime("%d.%m.%Y")) } ),
				SimpleHtmlHelper.tag_params(params),
				date_field.strftime("%d.%m.%Y"),
			)
		return date_field.strftime("%d.%m.%Y")

	@staticmethod
	def datetime(date_field, ucr=None, params=None):
		if date_field is None:
			return ''
		if ucr:
			return ("<a %s %s>%s</a> %s") % (
				SimpleHtmlHelper.tag_params( {'href': ucr(date=date_field.strftime("%d.%m.%Y")) } ),
				SimpleHtmlHelper.tag_params(params),
				date_field.strftime("%d.%m.%Y"),
				date_field.strftime("%H:%M")
			)
		return date_field.strftime("%d.%m.%Y %H:%M")

	@staticmethod
	def IterMonths(begin, end):

		if (begin.year*100+begin.month) > (end.year*100+end.month):
			return

		for year in range( begin.year, end.year+1 ):

			for month in range(1, 13):

				if year == begin.year and month < begin.month:
					continue
				if year == end.year and month > end.month:
					break

				yield (year, month)

	@staticmethod
	def SchemaOrgTime(date):
		if date is None:
			return ''
		if isinstance(date, datetime.datetime):
			return date.strftime("%Y-%m-%dT%H:%M:%S")
		return date.strftime("%Y-%m-%d")

	@staticmethod
	def PrettyTime(date, now=None):
		if date is None:
			return ''
		if isinstance(date, int):
			date = converters.int2datetime(date)
		now = now or datetime.datetime.now()
		if isinstance(date, datetime.datetime):
			if now.date() == date.date():
				return "Dziś {}".format( date.strftime("%H:%M") )
			return date.strftime("%d.%m.%Y")
		else:
			if now.date() == date:
				return "Dziś"
			return date.strftime("%d.%m.%Y")

	PrityTime = PrettyTime

	@classmethod
	def PrettyTimeLong(cls, date, now=None):
		if date is None:
			return ''
		if isinstance(date, int):
			date = converters.int2datetime(date)
		now = datetime.datetime.now() if now is None else now
		if isinstance(date, datetime.datetime):
			if now and now.date() == date.date():
				return "Dziś {}".format( date.strftime("%H:%M") )
			return "{} {} {}".format(date.day, cls.Mth2PL_lower[date.month], date.year)
		else:
			if now and now.date() == date:
				return "Dziś"
			return "{} {} {}".format(date.day, cls.Mth2PL_lower[date.month], date.year)

	@classmethod
	def PrettyDateTimeLong(cls, date, now=None):
		now = datetime.datetime.now() if now is None else now
		if now and now.date() == date:
			return cls.PrettyTimeLong(date, now)
		else:
			return "{}, godz.: {}".format(cls.PrettyTimeLong(date, now), date.strftime("%H:%M"))

	@staticmethod
	def form_begin(func, attr={}, **kwattr):

		all_attr={}
		all_attr.update(attr)
		all_attr.update(kwattr)

		if func:
			target = "%s.%s" % (func.__self__.__class__._public_id, func.action_hash)
			form_id = all_attr.pop('id', None)
		else:
			target = None
			form_id = all_attr.pop('id', None) or ''

		# 
		# enctype: "multipart/form-data"
		all_attr.setdefault("enctype", "application/x-www-form-urlencoded")
		all_attr.setdefault("action", "")
		all_attr.setdefault("method", "post")

		if form_id:
			all_attr.setdefault("name", form_id)
			all_attr.setdefault("id", form_id)

		if not isinstance(all_attr['action'], str):
			all_attr['action'] = all_attr['action']()

		all_attr = " ".join(['%s="%s"' % (k, filters.html_escape(v)) for k, v in list(all_attr.items())])

		target_input = """<input type="hidden" name="__action_target" value="{}" />""".format(target) if target else ""

		return Markup("""<form {}>{}""".format(all_attr, target_input))

	@staticmethod
	def form_end():
		return Markup("""</form>""")

	@staticmethod
	def input_hidden(name, value):
		return Markup('<input type="hidden" name="%s" value="%s" />' % (filters.html_escape(str(name)), filters.html_escape(str(value))))

	wiszace_znaki = re.compile('(^|\s)(a|i|o|u|w|z|I)(\s+)')

	@classmethod
	def Title2nobr(cls, text):
		"""
			"koniec lini z kropka" => "koniec lini z&nbsp;kropka"
		"""
		return Markup(cls.wiszace_znaki.sub(r'\1\2&nbsp;', str(filters.html_escape(text)) ))

	title2nobr = Title2nobr

	@staticmethod
	def packer(seq, items):
		buf=[]
		for i in seq:
			buf.append(i)
			if len(buf) == items:
				yield buf
				buf = []
		if len(buf):
			yield buf

	@staticmethod
	def ExtractSize(size):
		if not size:
			return None
		size = str(size).strip()
		if size.endswith('px'):
			return int(size[:-2])
		elif size.endswith('%'):
			return float(size[:-1])/100.0
		elif size.isdigit():
			return int(size)
		return None

	@staticmethod
	def Date(date_field, ucr=None, params=None):
		if date_field == None:
			return ''
		if ucr:
			return ("<a %s %s>%s</a>") % (
				HTMLHelper.tag_params( {'href': ucr(date=date_field.strftime("%Y-%m-%d")) } ),
				HTMLHelper.tag_params(params),
				date_field.strftime("%Y-%m-%d"),
			)
		return date_field.strftime("%Y-%m-%d")

	@staticmethod
	def Datetime(date_field, ucr=None, params=None):
		if date_field is None:
			return ''
		if ucr:
			return ("<a %s %s>%s</a> %s") % (
				HTMLHelper.tag_params( {'href': ucr(date=date_field.strftime("%Y-%m-%d")) } ),
				HTMLHelper.tag_params(params),
				date_field.strftime("%Y-%m-%d"),
				date_field.strftime("%H:%M")
			)
		return date_field.strftime("%Y-%m-%d %H:%M")

	@staticmethod
	def IterMonths(begin, end):

		if (begin.year*100+begin.month) > (end.year*100+end.month):
			return

		for year in range( begin.year, end.year+1 ):

			for month in range(1, 13):

				if year == begin.year and month < begin.month:
					continue
				if year == end.year and month > end.month:
					break

				yield (year, month)

	@staticmethod
	def Price(price, format=True):
		if format:
			return Markup('{}<small>,{:02d}</small>'.format(int(price/100), price%100))
		return '{},{:02d}'.format(int(price/100), price%100)

	@staticmethod
	def PrettyTime(date, now=None):
		if date is None:
			return ''
		# if isinstance(date, int):
		#	date = converters.int2datetime(date)
		now = now or datetime.datetime.now()
		if isinstance(date, datetime.datetime):
			if now.date() == date.date():
				return "Dziś {}".format( date.strftime("%H:%M") )
			return date.strftime("%d.%m.%Y")
		else:
			if now.date() == date:
				return "Dziś"
			return date.strftime("%d.%m.%Y")

	@staticmethod
	def PrettySize(size):
		for x, y in [ ('bajtów',0),('KB',0),('MB',2),('GB',2)]:
			if size < 200.0 and size > -200.0:
				if size == int(size):
					y = 0
				return ("%3."+str(y)+"f%s") % (size, x)
			size /= 1024.0
		return "%3.1f%s" % (size, 'TB')

	@staticmethod
	def Ellipsis(text, max_len=30):
		if len(text) > max_len:
			return text[:max_len] + "..."
		return text

	@staticmethod
	def FormBegin(func, attr={}, **kwattr):

		all_attr={}
		all_attr.update(attr)
		all_attr.update(kwattr)

		target = "%s.%s" % (func.__self__.__class__._public_id, func.action_hash)
		form_id = all_attr.pop('id', None)

		# 
		# enctype: "multipart/form-data"
		std_attr = {"id":form_id, "name":form_id, "enctype":"application/x-www-form-urlencoded", "action":"", "method":"post"}
		std_attr.update(all_attr)

		all_attr = " ".join(['%s="%s"' % (filters.html_escape(k), filters.html_escape(v)) for k, v in list(std_attr.items())])

		return Markup("""<form %s>
			<input type="hidden" name="__action_target" value="%s" />
		""" % (all_attr,target))

	@staticmethod
	def FormEnd():
		return Markup("""</form>""")

	@staticmethod
	def InputHidden(name, value):
		return Markup('<input type="hidden" name="%s" value="%s" />' % (filters.html_escape(str(name)), filters.html_escape(str(value))))

	@staticmethod
	def Packer(seq, items):
		buf=[]
		for i in seq:
			buf.append(i)
			if len(buf) == items:
				yield buf
				buf = []
		if len(buf):
			yield buf

	@staticmethod
	def ColumnsSpliter(seq, parts):
		l = len(seq)
		if l:
			last=0
			p = l//parts
			for i in range(parts):
				to=last+p + (1 if l-last > (parts-i)*p else 0)
				yield seq[last:to]
				last=to

	@staticmethod
	def urlencode(__data=None, **kwargs):
		return urllib.parse.urlencode(__data or kwargs)


try:
	from html2text import HTML2Text

	def html2text(content):
		h = HTML2Text()
		h.links_each_paragraph = False
		h.body_width = 0
		h.skip_internal_links = True
		h.inline_links = False
		h.ignore_links = True
		h.ignore_images = True
		h.ignore_emphasis = True
		h.google_doc = False
		h.ul_item_mark = ''
		h.emphasis_mark = ''
		h.strong_mark = ''

		return h.handle(content)

except ImportError:
	pass

StdHTMLHelper = HTMLHelpers
