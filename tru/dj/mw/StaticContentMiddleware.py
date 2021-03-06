import re

from django.conf import settings
from django.urls.resolvers import URLResolver, RegexPattern
from django.urls import Resolver404
from django.http import Http404, HttpResponseNotFound


def StaticContentMiddleware(get_response):

	def process_request(request):

		resolver = URLResolver(RegexPattern(r'^/'), settings.ROOT_URLCONF)
		try:
			callback, callback_args, callback_kwargs = resolver.resolve(request.path)
			return callback(request, *callback_args, **callback_kwargs)
		except Resolver404 as e:
			pass
		except Http404 as e:
			return HttpResponseNotFound(str(e))

		return get_response(request)

	return process_request
