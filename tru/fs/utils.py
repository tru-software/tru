import os
import re
import sys
import datetime
import logging
import time
import zlib
import hashlib
import ctypes
import random
import shutil
from pathlib import Path

from ..io import converters

log = logging.getLogger(__name__)


def fix_filename(filename):
	""" """

	f = converters.replace2ascii(filename.replace(' ', '_').replace('/', '').replace('\\', ''))

	m1 = re.compile('([-\'\"]+)')
	m2 = re.compile('([^A-Za-z0-9\\._]+)')
	m3 = re.compile('\s')
	f = m3.sub('', m2.sub(' ', m1.sub('', f)).strip())

	if len(f) < 2:
		raise Exception('Zbyt niepoprawna nazwa pliku')

	if len(f) > 32:
		return f[-32:]

	return f


def MakeDirs(filepath, ex_cls=OSError):
	dir = os.path.dirname(filepath)
	if not os.path.isdir(dir):
		try:
			os.makedirs(dir)
		except OSError as ex:
			raise ex_cls('Cannot create a directory {}: {}'.format(dir, ex))


def upload_file(post_file_dict, path, filename):

	# FIXME: Ensure if it is unique

	rel_path = path.rstrip('/')

	if not os.access(rel_path, 0):
		os.makedirs(rel_path)

	filepath = os.path.join(rel_path, filename)

	with open(filepath, "wb") as f:
		f.write(post_file_dict.read())

	return os.stat(filepath)[6]


def path_replace_ext(path, ext=None, append=''):
	""" Zmienia rozszrzerzenie pliku w podanej scieżce opcjonalnie dodaje postfix do nazwy pliku.
	path_replace_ext('filename.ext1', 'ext2') == 'filename.ext2'
	path_replace_ext('filename.ext1', 'ext2', '_x') == 'filename_x.ext2'
	path_replace_ext('filename.ext1, None, '_x') == 'filename_x.ext1'
	path_replace_ext('filename', 'xxx') == 'filename.xxx'

	inny kod który może być lepszy:
		DIR = settings.UPLOAD_DIR + '/'
		jpg = '.'.join( self.path.split('.')[:-1] ) + '.jpg'

	"""
	basename, path_ext = os.path.splitext(os.path.basename(path))
	return os.path.dirname(path) + "/" + basename + append + ('.' + ext if ext is not None else path_ext)


def Download(url):
	import httplib2
	h = httplib2.Http()
	resp, content = h.request(url)
	return resp['status'], content

	# import urllib
	# remote=urllib.urlopen(token_url)
	# content = remote.read()
	# status = remote.getcode()
	# remote.close()
	# return status, content


try:
	# PY3
	from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit
except ImportError:
	# PY2
	from urllib.parse import parse_qs, urlsplit, urlunsplit
	from urllib.parse import urlencode


def UpgradeURL(url, params):
	"""Given a URL, set or replace a query parameter and return the
	modified URL.

	>>> set_query_parameter('http://example.com?foo=bar&biz=baz', 'foo', 'stuff')
	'http://example.com?foo=stuff&biz=baz'

	"""

	scheme, netloc, path, query_string, fragment = urlsplit(url)
	query_params = parse_qs(query_string)

	for param_name, param_value in list(params.items()):
		query_params[param_name] = [param_value]

	new_query_string = urlencode(query_params, doseq=True)

	return urlunsplit((scheme, netloc, path, new_query_string, fragment))


def FileNameExtension(fileName):
	filename, extension = os.path.splitext(fileName)
	return extension


def GetCRCForData(data):
	csum = 0
	if hasattr(data, 'read'):
		while True:
			buf = data.read(4 * 1024)
			if not buf:
				break
			if csum is None:
				csum = zlib.crc32(buf)
			else:
				csum = zlib.crc32(buf, csum)
	else:
		for i in range(0, len(data), 4 * 1024):
			if csum is None:
				csum = zlib.crc32(data[i:i + 4 * 1024])
			else:
				csum = zlib.crc32(data[i:i + 4 * 1024], csum)
	return ctypes.c_int(csum & 0xFFFFFFFF).value


def GetSHA1ForData(data):

	h = hashlib.sha256()

	if hasattr(data, 'read'):
		while True:
			buf = data.read(4 * 1024)
			if not buf:
				break
			h.update(buf)
	else:
		if isinstance(data, str):
			data = data.encode()

		# To ma w ogóle sens?
		for i in range(0, len(data), 4 * 1024):
			h.update(data[i:i + 4 * 1024])

	return h.hexdigest()


def CreateCrcLinkCRC32(filename, dir, urldir):

	prev = 0
	with open(dir + '/' + filename, "rb") as fd:
		for content in fd.read(1024):
			prev = zlib.crc32(content, prev)

	return "%s/%s?_=%X" % (urldir.rstrip('/'), filename, (prev & 0xFFFFFFFF))


def CreateCrcLinkMD5(filename, dir, urldir, block_size=1024 * 8):

	md5 = hashlib.md5()
	with open(dir + '/' + filename, "rb") as f:
		while True:
			data = f.read(block_size)
			if not data:
				break
			md5.update(data)
	return "%s/%s?_=%s" % (urldir.rstrip('/'), filename, md5.hexdigest())


CreateCrcLink = CreateCrcLinkMD5


class TmpFile:
	def __init__(self, filepath, mode='wb', perms=None):

		self.filepath = filepath
		self.filepath_tmp = filepath + '.RND{}.tmp'.format(random.randrange(0xffffffff))
		os.makedirs(os.path.dirname(filepath), exist_ok=True)
		self.f = open(self.filepath_tmp, mode=mode)
		self.perms = perms

	def __enter__(self):
		return self.f

	def __exit__(self, exc_type, exc_value, traceback):
		self.f.close()
		tmp = self.filepath_tmp
		if exc_type is None:
			if self.perms is not None:
				os.chmod(tmp, self.perms)
			os.rename(tmp, self.filepath)
		else:
			try:
				os.remove(tmp)
			except IOError:
				pass
		return False


class TmpDir:
	def __init__(self, base_dir, perms=None):

		self.base_dir = base_dir
		self.base_dir_tmp = '{}.RND{}.tmp'.format(str(base_dir).rstrip('/'), random.randrange(0xffffffff))
		self.perms = perms

		if os.path.exists(self.base_dir_tmp):
			raise IOError(f"Cannot create tmp dir under {self.base_dir_tmp}")

		os.makedirs(self.base_dir_tmp, exist_ok=True)
		os.chmod(self.base_dir_tmp, 0o700)

	def __enter__(self):
		return Path(self.base_dir_tmp)

	def __exit__(self, exc_type, exc_value, traceback):

		if exc_type is None:
			if self.perms is not None:
				os.chmod(self.base_dir_tmp, self.perms)

			new_tmp = '{}.RND{}.tmp'.format(str(self.base_dir).rstrip('/'), random.randrange(0xffffffff))

			if os.path.exists(new_tmp):
				raise IOError(f"Cannot create tmp dir under {new_tmp}")

			if os.path.exists(self.base_dir):
				os.rename(self.base_dir, new_tmp)
				os.rename(self.base_dir_tmp, self.base_dir)
				shutil.rmtree(new_tmp)
			else:
				os.rename(self.base_dir_tmp, self.base_dir)
		else:
			try:
				shutil.rmtree(self.base_dir_tmp)
			except IOError:
				log.warn(f"TmpDir: cannot remove tmp dir {self.base_dir_tmp}")

		return False


def utf8(s):
	if isinstance(s, bytes):
		return s.decode()
	return s


def FindFileExt(dir_name, base_name):

	for i in ('jpg', 'JPG', 'png', 'tif', 'jpeg', 'gif', 'tiff', 'PNG', 'GIF'):
		if os.path.isfile(utf8(os.path.join(dir_name, base_name + i))):
			return i
	else:
		for i in os.listdir(utf8(dir_name)):
			if i.startswith(base_name) and os.path.isfile(utf8(os.path.join(dir_name, i))):
				return i[i.rfind('.') + 1:]

	return None
