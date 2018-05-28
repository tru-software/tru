# -*- coding: utf-8 -*-

import os
import sys
import datetime
import time
import logging
import re
from mako import filters
import unicodedata
import base64
import pickle as pickle
import traceback

from . import icu

# from django.utils.http import cookie_date

log = logging.getLogger(__name__)

# ------------------------------------------------------------------------

def plain_text2html(text):
	return str(filters.html_escape(text)).replace('\n', '<br/>')

# ------------------------------------------------------------------------

def str2datetime(date):
	if not date:
		return None
	try:
		if len(date) > len('2007-12-12') :
			return datetime.datetime.fromtimestamp( time.mktime(time.strptime(date, '%Y-%m-%dT%H:%M:%S') ) )
		return datetime.datetime.fromtimestamp( time.mktime(time.strptime(date, '%Y-%m-%d') ) )
	except Exception as ex:
		raise Exception("Nie można rozpoznać daty z '%s': %s" % (date, ex))

# ------------------------------------------------------------------------

def str2date(date):
	if not date:
		return None
	try:
		if len(date) > len('2007-12-12') :
			return datetime.datetime.fromtimestamp( time.mktime(time.strptime(date, '%Y-%m-%dT%H:%M:%S') ) )
		
		return datetime.datetime.fromtimestamp( time.mktime(time.strptime(date, '%Y-%m-%d') ) )
	except Exception as ex:
		raise Exception("Nie można rozpoznać daty z '%s': %s" % (date, ex))

# ------------------------------------------------------------------------

def date2rfc2822(date):
	if date.tzinfo:
		time_str = date.strftime('%a, %d %b %Y %H:%M:%S ')
		offset = date.tzinfo.utcoffset(date)
		timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
		hour, minute = divmod(timezone, 60)
		return time_str + "%+03d%02d" % (hour, minute)
	else:
		return date.strftime('%a, %d %b %Y %H:%M:%S -0000')

# ------------------------------------------------------------------------

def date2cookie(date):
	# TODO: cookie_date
	return date2rfc2822(date)

# ------------------------------------------------------------------------

def date2rfc3339(date):
	if date.tzinfo:
		time_str = date.strftime('%Y-%m-%dT%H:%M:%S')
		offset = date.tzinfo.utcoffset(date)
		timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
		hour, minute = divmod(timezone, 60)
		return time_str + "%+03d:%02d" % (hour, minute)
	else:
		return date.strftime('%Y-%m-%dT%H:%M:%SZ')

# ------------------------------------------------------------------------

def datetime2json_plain(date, above1900=False):
	if date is None:
		return None
	if above1900 and date.year < 1900:
		return None
	return date.strftime('%F %X')

# ------------------------------------------------------------------------

def date2json(date, above1900=False):
	if date is None:
		return None
	if above1900 and date.year < 1900:
		return None
	return date.strftime('%Y-%m-%d')

# ------------------------------------------------------------------------

def date2str(date_field):
	return date_field.strftime("%Y-%m-%d")

# ------------------------------------------------------------------------

def datetime2str(date_field, default=None):
	return date_field.strftime("%Y-%m-%d %H:%M") if date_field else default

# ------------------------------------------------------------------------
# ------------------------------------------------------------------------

def datetime2json(date):
	if date is None:
		return None
	return date.strftime(date.isoformat())

def json2datetime(sdate):
	'2011-05-25T20:34:05.787Z'
	if sdate is None:
		return None
	if sdate.endswith('Z'):
		return datetime.datetime.strptime(sdate, '%Y-%m-%dT%H:%M:%S.%fZ')
	return datetime.datetime.strptime(sdate, '%Y-%m-%dT%H:%M:%S.%f')

# ------------------------------------------------------------------------
# ------------------------------------------------------------------------


def unique_timeid():
	try:
		return int( datetime.datetime.now().strftime('%s') )
	except:
		return str(time.mktime(datetime.datetime.now().timetuple())).replace('.','')
	return 0


def datetime2int(date):

	if date is None:
		return None
	return int(time.mktime(date.timetuple()))

# ------------------------------------------------------------------------

def int2datetime(date):

	if date is None:
		return None
	return datetime.datetime.fromtimestamp(date)

# ------------------------------------------------------------------------

def strtr(text, dict):
	if isinstance(text, bytes):
		text = text.decode('utf8')
	return ''.join((dict.get(i, i) for i in text))

# -----------------------------------------------------------------------------

def fbdate2date(date_str):
	return datetime.datetime.fromtimestamp(time.mktime(time.strptime(date_str, '%m/%d/%Y')))

# -----------------------------------------------------------------------------

def ParsePrice(x):
	if not x:
		return None
	return max(int(float(str(x).replace(' ', '').replace(',', '.'))*100), 0) or None


def FormatPrice(price):
	if not price:
		return ''
	return '{},{:02d}'.format(price/100, price%100) if price else ''

# -----------------------------------------------------------------------------

pl2lat = {
	'ś' : 's',
	'ś' : 's',
	'ą' : 'a',
	'ę' : 'e',
	'ć' : 'c',
	'ź' : 'z',
	'ż' : 'z',
	'ó' : 'o',
	'ł' : 'l',
	'ę' : 'e',
	'ń' : 'n',
	'Ś' : 'S',
	'Ą' : 'A',
	'Ę' : 'E',
	'Ć' : 'C',
	'Ź' : 'Z',
	'Ż' : 'Z',
	'Ó' : 'O',
	'Ł' : 'L',
	'Ę' : 'E',
	'Ń' : 'N'
}

# ------------------------------------------------------------------------

def replace2ascii(text):
	if not text:
		return ''
	return strtr(text, pl2lat)

# ------------------------------------------------------------------------

m1 = re.compile('([\'\"]+)')
m2 = re.compile('([^A-Za-z0-9]+)')
m3 = re.compile('\s')

def title2slug(text, delimiter='-', maxlen=64):
	if not text:
		return ''

	if not isinstance(text, str):
		text = str(text)

	text = replace2ascii(text)
	text = m3.sub(delimiter, m2.sub(' ', m1.sub('', text)).strip())
	if len(text) > maxlen:
		text = text[:maxlen]
		f = text.rfind('-')
		if f == -1 or f == 0:
			return text
		return text[:f]
	return text

# -----------------------------------------------------------------------------

def dict2str(d):
	if not d:
		return ''

	# return repr(d)
	return base64.encodestring(pickle.dumps(d, pickle.HIGHEST_PROTOCOL)).decode('ascii')

# -----------------------------------------------------------------------------

def str2dict(s):
	if not s or s == 'None':
		return {}
	# try:

	if s.startswith('{'):
		return eval(s)

	if isinstance(s, str):
		s = s.encode('ascii')

	return pickle.loads(base64.decodestring(s))
	#except Exception as ex:
	#	log.error( "Nie można zdeserializować wartości: %s\n%s\n\n%s" % (ex, str('\n'.join(traceback.format_exception(ex)), 'UTF8')), s )
	return {}

# -----------------------------------------------------------------------------

#/**
#* Takes the input and does a "special" case fold. It does minor normalization
#* and returns NFKC compatable text
#*
#* @param	string	$text	text to be case folded
#* @param	string	$option	determines how we will fold the cases
#* @return	string			case folded text
#*/
fc_nfkc_closure = icu.fc_nfkc_closure

# -----------------------------------------------------------------------------

# case_fold_c.php
uniarray_c = icu.uniarray_c


# case_fold_f.php
uniarray_f = icu.uniarray_f

# case_fold_s.php
uniarray_s = icu.uniarray_s


# -----------------------------------------------------------------------------

#/**
#* Case folds a unicode string as per Unicode 5.0, section 3.13
#*
#* @param	string	$text	text to be case folded
#* @param	string	$option	determines how we will fold the cases
#* @return	string			case folded text
#*/
def utf8_case_fold(text, option='full'):
	# // common is always replaced
	text = strtr(text, uniarray_c);

	if option == 'full':
		# // full replaces a character with multiple characters
		text = strtr(text, uniarray_f)
	else:
		# // simple replaces a character with another character
		text = strtr(text, uniarray_s)

	return text;

# -----------------------------------------------------------------------------

def utf8_case_fold_nfkc(text, option='full'):
	text = utf8_case_fold(text, option);

	#// convert to NFKC
	# utf_normalizer::nfkc($text);
	text = unicodedata.normalize('NFKC', text)

	#// FC_NFKC_Closure, http://www.unicode.org/Public/5.0.0/ucd/DerivedNormalizationProps.txt
	text = strtr(text, fc_nfkc_closure)

	return text;

# -----------------------------------------------------------------------------

#/**
#* This function is used to generate a "clean" version of a string.
#* Clean means that it is a case insensitive form (case folding) and that it is normalized (NFC).
#* Additionally a homographs of one character are transformed into one specific character (preferably ASCII
#* if it is an ASCII character).
#*
#* Please be aware that if you change something within this function or within
#* functions used here you need to rebuild/update the username_clean column in the users table. And all other
#* columns that store a clean string otherwise you will break this functionality.
#*
#* @param	string	$text	An unclean string, mabye user input (has to be valid UTF-8!)
#* @return	string			Cleaned up version of the input string
#*/
homographs = icu.homographs


def utf8_clean_string(text):

	text = utf8_case_fold_nfkc(text)
	text = strtr(text, homographs)

	#// Other control characters
	# $text = preg_replace('#(?:[\x00-\x1F\x7F]+|(?:\xC2[\x80-\x9F])+)#', '', $text);
	text = re.sub(r'#(?:[\x00-\x1F\x7F]+|(?:\xC2[\x80-\x9F])+)#', '', text)

	#// we need to reduce multiple spaces to a single one
	# $text = preg_replace('# {2,}#', ' ', $text);
	text = re.sub(r'# {2,}#', ' ', text)

	#// we can use trim here as all the other space characters should have been turned
	#// into normal ASCII spaces by now
	return text.strip()  # trim($text);

# -----------------------------------------------------------------------------

def unpack(array):
	for i in array:
		if isinstance(i, (list, tuple)):
			for x in unpack(i):
				yield x
		else:
			yield i

# -----------------------------------------------------------------------------

def getint(v):
	try:
		return int(v)
	except:
		return 0

# -------------------------------------------------------------------------------------------

def make_encoder(baseString):
	size = len(baseString)
	d = {ch: i for (i, ch) in enumerate(baseString)}
	if len(d) != size:
		raise ValueError("Duplicate characters in encoding string")

	def encode(x):
		if x == 0:
			return baseString[0]  # Only needed if don't want '' for 0
		l = []
		while x > 0:
			l.append(baseString[x % size])
			x //= size
		return ''.join(l)

	def decode(s):
		return sum(d[ch] * size**i for (i, ch) in enumerate(s))

	return encode, decode
