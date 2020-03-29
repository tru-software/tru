from django.http import HttpRequest

__all__ = ["LazyFullURL", "LazyFullURLProtocol"]


class LazyFullURL:
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_full_url'):
			full_url = '%s%s' % (request.environ.get('HTTP_HOST', '<HOST>'), request.environ.get('PATH_INFO', '<PATH>'))
			if request.environ.get('QUERY_STRING', None):
				full_url += '?' + request.environ['QUERY_STRING']
			request._full_url = full_url
		return request._full_url


HttpRequest.full_url = LazyFullURL()


class LazyFullURLProtocol:
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_full_url_protocol'):
			request._full_url_protocol = ('https://' if request.is_secure() else 'http://') + request.full_url
		return request._full_url_protocol


HttpRequest.full_url_protocol = LazyFullURLProtocol()


class LazyMethodHostPathQueryString:
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_method_host_path'):
			request._method_host_path = "{} '{}'".format(request.environ['REQUEST_METHOD'], request.full_url_protocol)
		return request._method_host_path


HttpRequest.method_host_path = LazyMethodHostPathQueryString()
