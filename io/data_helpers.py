# -*- coding: utf-8 -*-

import re
import datetime
import hashlib

from django.utils.html import simple_email_re as email_re


# ----------------------------------------------------------------------------

def IsValidEmail(email):
    return bool(email_re.match(email))

# ----------------------------------------------------------------------------

postcode_re = re.compile("^[0-9]{3}\-[0-9]{2}$")
def IsValidPostcode(postcode):
	return bool(postcode_re.match(postcode))

# ----------------------------------------------------------------------------

from decimal import Decimal
def ParsePrice(price):
	
	price = str(price).replace(",", ".").replace(" ", "").strip()
	if not price or not re.match("^[0-9]+(\.[0-9]{1,2})?$", price):
		raise ValueError("Nieprawidłowa wartość liczbowa")
	
	return int(Decimal(price) * 100)

# ----------------------------------------------------------------------------

def TimeInRange(time_range, now=None):
	now = now or datetime.datetime.now()
	return (now.hour * 100 + now.minute) in time_range

# -------------------------------------------------------------------------------

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
