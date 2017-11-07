# -*- coding: utf-8 -*-

import os
import logging
import hashlib
import base64
import version

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------

def CreateCrcLinkMD5(filename, block_size=1024*8):

	md5 = hashlib.md5()
	with open(filename,"rb") as f:
		while True:
			data = f.read(block_size)
			if not data:
				break
			md5.update(data)
	return base64.urlsafe_b64encode(md5.digest()).rstrip('=').replace('-', '')

# ----------------------------------------------------------------------------

_crc_cache = {}

def Mark(filename, dir, netloc='', debug=False):

	if not netloc.endswith('/'):
		netloc += '/'

	if not dir.endswith('/'):
		dir += '/'

	if debug:
		return netloc+filename

	filepath = dir+filename

	filepath_crc = _crc_cache.get(filepath)
	if filepath_crc is None:
		crc = CreateCrcLinkMD5(filepath) if os.path.isfile(filepath) else version.svn_rev
		filepath_crc = '{}{}?_={}'.format(netloc, filename.lstrip('/'), crc)
		_crc_cache[filepath] = filepath_crc

		#log.info(u"Obliczenie CRC dla {}: {}".format(filepath, crc))

	return filepath_crc

# ----------------------------------------------------------------------------
	