# -*- coding: utf-8 -*-

import re

import settings
from django.core import urlresolvers
from django.urls import Resolver404

def StaticContentMiddleware(get_response):

	def process_request(request):

		resolver = urlresolvers.RegexURLResolver(r'^/', settings.ROOT_URLCONF)

		try:
			callback, callback_args, callback_kwargs = resolver.resolve(request.path)
			return callback(request, *callback_args, **callback_kwargs)
		except Resolver404 as e:
			pass

		return get_response(request)

	return process_request
