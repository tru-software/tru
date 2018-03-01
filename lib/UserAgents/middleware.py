# -*- coding: utf-8 -*-

import re
import logging
from pyutils import GetTraceback

from .checker import CheckBot, CheckMobile

log    = logging.getLogger(__name__)

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


def Setup(func):
	global GetCookiePrefix
	GetCookiePrefix = func

def GetCookiePrefix(request):
	return ''


class LazyIsBot(object):

	__slots__ = tuple()

	## TODO: .IsBot jest wywoływany dla każdego requestu (ze względu na access log)
	## mino, że to nie jest potrzebne.

	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_cached_isbot'):
			remote_addr = request.META['REMOTE_ADDR']
			if proper_IPv4.match(remote_addr):
				try:
					request._cached_isbot = True if hasattr(request, '_broken_remote_addr') else CheckBot(remote_addr, request.META['HTTP_USER_AGENT'])
				except Exception as ex:
					log.error('Cannot check bot ({}, {}): {}\n{}'.format(remote_addr, request.META['HTTP_USER_AGENT'], str(ex), GetTraceback(ex)))
					request._cached_isbot = True
			else:
				request._cached_isbot = True
		return request._cached_isbot


class LazyIsMobileBrowser(object):

	__slots__ = tuple()

	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_cached_ismobilebrowser'):
			request._cached_ismobilebrowser = False

			mobile = request.COOKIES.get(GetCookiePrefix(request)+'ForceLayouts', 'auto')
			if mobile == 'mobile':
				request._cached_ismobilebrowser = True
			elif mobile == 'desktop':
				request._cached_ismobilebrowser = False
			elif 'HTTP_USER_AGENT' in request.META:
				request._cached_ismobilebrowser = CheckMobile(request.META['HTTP_USER_AGENT'])

		return request._cached_ismobilebrowser
