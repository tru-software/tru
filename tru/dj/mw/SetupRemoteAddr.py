import re
from django.conf import settings
import logging

from django.http import HttpResponseNotFound

from ...utils.backtrace import GetTraceback
from .CatchExceptions import CatchExceptions


log = logging.getLogger(__name__)

proper_IPv4 = re.compile(r'^[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*$')
proper_IPv6 = re.compile(r"""
        ^
        \s*                         # Leading whitespace
        (?!.*::.*::)                # Only a single whildcard allowed
        (?:(?!:)|:(?=:))            # Colon iff it would be part of a wildcard
        (?:                         # Repeat 6 times:
            [0-9a-f]{0,4}           #   A group of at most four hexadecimal digits
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
        ){6}                        #
        (?:                         # Either
            [0-9a-f]{0,4}           #   Another group
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
            [0-9a-f]{0,4}           #   Last group
            (?: (?<=::)             #   Colon iff preceeded by exacly one colon
             |  (?<!:)              #
             |  (?<=:) (?<!::) :    #
             )                      # OR
         |                          #   A v4 address with NO leading zeros 
            (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            (?: \.
                (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            ){3}
        )
        \s*                         # Trailing whitespace
        $""", re.VERBOSE | re.IGNORECASE | re.DOTALL)


def SetupRemoteAddr(get_response):
	"""
	Middleware that sets REMOTE_ADDR based on HTTP_X_FORWARDED_FOR, if the
	latter is set. This is useful if you're sitting behind a reverse proxy that
	causes each request's REMOTE_ADDR to be set to 127.0.0.1.

	Note that this does NOT validate HTTP_X_FORWARDED_FOR. If you're not behind
	a reverse proxy that sets HTTP_X_FORWARDED_FOR automatically, do not use
	this middleware. Anybody can spoof the value of HTTP_X_FORWARDED_FOR, and
	because this sets REMOTE_ADDR based on HTTP_X_FORWARDED_FOR, that means
	anybody can "fake" their IP address. Only use this when you can absolutely
	trust the value of HTTP_X_FORWARDED_FOR.
	"""

	INTERNAL_ADDRS = list(map(re.compile, getattr(settings, 'INTERNAL_ADDRS', [])))

	@CatchExceptions
	def middleware(request):

		request.IsBot = False

		# request.META['REMOTE_ADDR'] = "2601:582:4003:ea10:c97d:259f:ec7e:604a"

		# Obsługa HaProxy lub/i nginx:

		# HTTP_X_FORWARDED_FOR can be a comma-separated list of IPs. The
		# client's IP will be the first one.
		if 'HTTP_X_FORWARDED_FOR' in request.META:
			for i in request.META['HTTP_X_FORWARDED_FOR'].split(','):
				i = i.strip()
				request.META['REMOTE_ADDR'] = i
				if i != 'unknown':
					break
				request._broken_remote_addr = True

		if 'HTTP_USER_AGENT' not in request.META:
			request._broken_remote_addr = True

		remote_addr = request.META['REMOTE_ADDR']
		if remote_addr == 'unknown' or not proper_IPv4.match(remote_addr):
			if not proper_IPv6.match(remote_addr):
				# FIXME: Http404 → HTTP400 - bad request
				return HttpResponseNotFound("Błędy REMOTE_ADDR='%s' z HTTP_X_FORWARDED_FOR='%s' dla %s '%s'" % (remote_addr, request.META.get('HTTP_X_FORWARDED_FOR', ''), request.environ['REQUEST_METHOD'], request.full_url))
			else:
				log.warn('Unsupported ipv6 adrress "{}" for "{}" ({})'.format(remote_addr, request.full_url, request.environ['REQUEST_METHOD']))

		for i in INTERNAL_ADDRS:
			if i.match(request.META['REMOTE_ADDR']):
				request.META['INTERNAL_ADDR'] = True
				break
		else:
			if 'INTERNAL_ADDR' in request.META:
				del request.META['INTERNAL_ADDR']

		return get_response(request)

	return middleware

# ----------------------------------------------------------------------------
