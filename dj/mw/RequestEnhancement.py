# -*- coding: utf-8 -*-

import re
import urllib
import logging
from django.conf import settings

from django.http import HttpRequest, HttpResponseBadRequest

from ...lib import UserAgents
from ...utils.backtrace import GetTraceback
from .CatchExceptions import CatchExceptions


class CheckOriginProtection:
	"""
		Simple protection against a CSRF attack.
		See also https://docs.djangoproject.com/en/2.0/topics/security/#cross-site-request-forgery-csrf-protection
	"""

	external_log = None

	def __init__(self, get_response):
		self.get_response = get_response
		self.log = self.external_log or logging.getLogger(__name__)

	def IsDomainRegistred(self, domain):
		return True

	def _check(self, request, origin):

		origin = origin.lower()
		url = urllib.parse.urlsplit(origin)
		if url.scheme not in ('http', 'https'):
			return False

		return url.hostname and self.IsDomainRegistred(url.hostname)

	#@CatchExceptions
	def __call__(self, request):

		if request.method in ('POST', 'DELETE', 'PUT'):

			origin = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_REFERER')
			if origin == 'null':
				origin = None
			if origin:
				# Przeglądarka przysłała HTTP_ORIGIN, który wygląda np. "http://example.pl/"

				if not self._check(request, origin):
					self.log.error("Incorrect Origin!!\nHTTP_ORIGIN: %s\nURL: %s\nPOST: %s\nMETA: %s\n" % (request.META.get('HTTP_ORIGIN'), request.full_url, request.POST, request.META))
					return HttpResponseBadRequest()
			else:
				# Jeżeli nie dostajemy oryginu, to znaczy, że request przychodzi od czegoś innego niż przeglądarka. Bot?
				request.IsBot = True

		return self.get_response(request)
