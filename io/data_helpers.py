# -*- coding: utf-8 -*-

import re
import datetime

from django.utils.html import simple_email_re as email_re

from .hash import get_hexdigest

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
