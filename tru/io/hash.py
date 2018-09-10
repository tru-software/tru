# -*- coding: utf-8 -*-

import re
import datetime
import hashlib
import string
import zlib
from hashlib import md5
import types

from . import converters

# ----------------------------------------------------------------------------

md5_constructor, sha_constructor = hashlib.md5, hashlib.sha1

def get_hexdigest(algorithm, salt, raw_password, hsh=None):
	"""
	Returns a string of the hexdigest of the given plaintext password and salt
	using the given algorithm ('md5', 'sha1' or 'crypt').
	"""

	from django.utils.encoding import smart_str

	raw_password, salt = smart_str(raw_password), smart_str(salt)

	if algorithm == 'md5':
		return md5_constructor((salt + raw_password).encode()).hexdigest()
	elif algorithm == 'sha1':
		return sha_constructor((salt + raw_password).encode()).hexdigest()
#	elif algorithm == '' and (salt == 'H' or salt == 'P'):
#		return phpass.crypt_private(raw_password.encode('utf-8'), hsh, hash_prefix="$%s$" % (salt) )
	log.error('Niepoprawny algorytm haszujący: %s' % (algorithm))
	return None
	# raise ValueError("Got unknown password algorithm type in password.")

# -------------------------------------------------------------------------------

def Hash_v1(text):

	if isinstance(text, dict):
		return Hash_v1('.'.join(("%s=%s;"%(k, Hash_v1(v)) for k, v in sorted(text.items()))))
	elif isinstance(text, (list, tuple, set, frozenset)):
		return Hash_v1(b"\n".join(map(bytes, map(Hash_v1, text))))
	elif isinstance(text, str):
		text = text.encode('utf8')

	if not isinstance(text, bytes):
		text = repr(text).encode('utf8')

	# adler32 is week!
	# see: https://www.leviathansecurity.com/blog/analysis-of-adler32
	return zlib.adler32(text) & 0xFFFFFFFF


def _extract(text):

	if isinstance(text, dict):
		for k, v in sorted(text.items()):
			yield from _extract(k)
			yield from _extract(v)
			yield b"\n"
	elif isinstance(text, types.GeneratorType):
		for t in text:
			yield from _extract(t)
			yield b"\n"
	elif isinstance(text, (list, tuple, set, frozenset)):
		for t in text:
			yield from _extract(t)
			yield b"\n"
	elif isinstance(text, str):
		yield text.encode('utf8')
	elif isinstance(text, bytes):
		yield text
	else:
		yield repr(text).encode('utf8')
	yield b"\n"


def Hash_v2(text):
	m = md5()

	if isinstance(text, str):
		m.update(text.encode('utf8'))
	elif isinstance(text, bytes):
		m.update(text)
	else:
		for i in _extract(text):
			m.update(i)
	return int(m.hexdigest(), 16)


def Hash_crc32(text):

	crc = 0

	if isinstance(text, str):
		crc = zlib.crc32(text.encode('utf8'))
	elif isinstance(text, bytes):
		crc = zlib.crc32(text)
	else:
		for i in _extract(text):
			crc = zlib.crc32(i, crc)

	return crc & 0xFFFFFFFF


Hash = Hash_v2
Hash32 = Hash_crc32


def Distribution(text, options):
	return Hash(text) % options

# -------------------------------------------------------------------------------

EncodeHash, DecodeHash = converters.make_encoder(string.digits + string.ascii_lowercase + string.ascii_uppercase)

# -------------------------------------------------------------------------------

def coalesce(*args):
	for i in args:
		if i is not None:
			return i

# -------------------------------------------------------------------------------
