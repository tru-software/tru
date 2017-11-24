# -*- coding: utf-8 -*-

import re
import datetime
import hashlib
import string
import zlib

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
		return md5_constructor(salt + raw_password).hexdigest()
	elif algorithm == 'sha1':
		return sha_constructor(salt + raw_password).hexdigest()
#	elif algorithm == '' and (salt == 'H' or salt == 'P'):
#		return phpass.crypt_private(raw_password.encode('utf-8'), hsh, hash_prefix="$%s$" % (salt) )
	log.error( 'Niepoprawny algorytm haszujący: %s' % (algorithm) )
	return None
	# raise ValueError("Got unknown password algorithm type in password.")

# -------------------------------------------------------------------------------


def Hash(text):
	return (zlib.adler32(text if isinstance(text, bytes) else text.encode('utf8')) & 0xFFFFFFFF)


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
