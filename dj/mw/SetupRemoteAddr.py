# -*- coding: utf-8 -*-

import settings

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

	INTERNAL_ADDRS = getattr(settings, 'INTERNAL_ADDRS', [])

	def middleware(request):

		request.IsBot = False

		# request.META['REMOTE_ADDR'] = "2601:582:4003:ea10:c97d:259f:ec7e:604a"

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
