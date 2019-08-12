import json
from urllib.parse import urlencode

from django.urls import reverse
from django.http import HttpRequest
from django.test.client import MULTIPART_CONTENT


class LazyFullURL(object):
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_full_url'):
			full_url = '%s%s' % ( request.environ.get('HTTP_HOST','<HOST>'), request.environ.get('PATH_INFO','<PATH>') )
			if request.environ.get('QUERY_STRING', None):
				full_url += '?' + request.environ['QUERY_STRING']
			request._full_url = full_url
		return request._full_url

class LazyFullURLProtocol(object):
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_full_url_protocol'):
			request._full_url_protocol = ('https://' if request.is_secure() else 'http://') + request.full_url
		return request._full_url_protocol


HttpRequest.full_url = LazyFullURL()
HttpRequest.full_url_protocol = LazyFullURLProtocol()


# echo 'from tru.dj.django_helpers import ProcessRequest; print(ProcessRequest("https://wre.pl:8000/"))' | ./manage.py shell
def ProcessRequest(url, method='GET', POST=None, headers={}, cookies={}, content_type=None):
	from django.test import RequestFactory
	request_factory = RequestFactory()

	from django.core.handlers.wsgi import WSGIHandler
	handler = WSGIHandler()
	
	from urllib.parse import urlparse, parse_qsl
	url_parts = urlparse(url)

	headers.update({
		'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.170 Safari/537.36',
		'HTTP_HOST': url_parts.netloc,
		'HTTP_X_SCHEME': url_parts.scheme,
	})

	if method == 'GET':
		query = parse_qsl(url_parts.query)
		request = request_factory.get(url_parts.path, query, **headers);
	elif method == 'POST':
		request = request_factory.post(url_parts.path, POST, content_type=content_type or MULTIPART_CONTENT,  **headers);
	else:
		raise ValueError("Unsupported method type: {}".format(method))
	
	for k,v in cookies.items():
		request.COOKIES[k] = v
	
	return handler.get_response(request)


def ProcessRequestJSON(url, data, method='POST', **kwargs):
	response = ProcessRequest(url, method=method, POST=data, content_type='application/json', **kwargs)

	if response['Content-Type'].startswith('application/json'):
		return json.loads(response.content)

	return response


class URLGenerator:

	def __init__(self, base_url=None):
		self.base_url = (base_url or '').rstrip('/')

	@classmethod
	def extract(cls, o):
		if hasattr(o, 'GetURLPart'):
			return o.GetURLPart()
		return o

	def generate(self, name, args, kwargs):
		query_string = ('?' + urlencode({k: self.extract(v) for k, v in kwargs.items()}, encoding="utf8")) if kwargs else ''
		return self.base_url + reverse(name, args=list(map(URLGenerator.extract, args))) + query_string

	def __getattr__(self, name):
		return lambda *a, **kw: self.generate(name, a, kw)
