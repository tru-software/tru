# -*- coding: utf-8 -*-

import json
from django.http import Http404, HttpResponseRedirect, HttpResponse

# -----------------------------------------------------------------------------

class WebException(Exception):

	def __init__(self, msg, help=None):
		self.help = help
		super(WebException, self).__init__(msg)

#	def __str__(self):
#		return self.message

	def serialize(self):
		return {'msg': str(self), 'type': self.__class__.__name__}

RequestException = WebException

# -----------------------------------------------------------------------------

class InputException(WebException):
	"""
		Użytkownik wpisał złą wartość w jakimś polu <input />
	"""

	def __init__(self, input_name, msg, help=None):
		self.input_name = input_name
		super(InputException, self).__init__(msg, help)

	def serialize(self):
		return {'type': self.__class__.__name__, 'msg': str(self), 'input': self.input_name}

# -----------------------------------------------------------------------------

class InternalException(WebException):
	"""
		Brakuje jakiś danych, coś się źle wczytało itp.
	"""

	def __init__(self, msg, help=None):
		super(InternalException, self).__init__(msg, help)

# -----------------------------------------------------------------------------

class AccessException(WebException):
	"""
		Użytkownik nie ma praw, albo coś w tym rodzaju.
	"""
	def __init__(self, profile, msg=None, help=None):
		# FIXME:
		if msg:
			super(AccessException, self).__init__(msg, help)
		else:
			super(AccessException, self).__init__(profile, help)

# -----------------------------------------------------------------------------

class LogicException(WebException):
	"""
		Operacja nie ma sensu.
	"""
	def __init__(self, msg=None, help=None):
		super(LogicException, self).__init__(msg, help)

# -----------------------------------------------------------------------------

class LoginException(WebException):
	"""
		Użytkownik musi się zalogować.
	"""
	def __init__(self, msg=None):
		super(LoginException, self).__init__(msg)

# -----------------------------------------------------------------------------

# -------------------------------------------------------------------------------

class RedirectWithJavaScriptResponse(HttpResponse):

	def __init__(self, url):
		## $(document).ready(function(){});
		code = """
<script type="text/javascript">
/* <![CDATA[ */
window.location.href = %s;
/* ]]> */
</script>
		""" % ( json.dumps( url ) );

		super(RedirectWithJavaScriptResponse, self).__init__( code )

# ----------------------------------------------------------------------------

class ResponseException(Exception):

	def __init__(self, response):
		super(ResponseException, self).__init__('response')
		self.response = response

# ----------------------------------------------------------------------------
