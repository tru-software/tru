# -*- coding: utf-8 -*-

from django.http import HttpResponse
import json


class WebException(Exception):

	__slots__ = ('args', 'message', 'help')

	def __init__(self, msg, help=None):
		self.help = help
		super(WebException, self).__init__(msg)

	def serialize(self):
		d = {'type': self.__class__.__name__, 'msg': str(self)}
		return d


class InputException(WebException):
	"""
		Użytkownik wpisał złą wartość w jakimś polu <input />
	"""

	__slots__ = ('args', 'message', 'help', 'msg_html', 'input_name')

	def __init__(self, input_name, msg, help=None, html=None):
		self.input_name = input_name
		self.msg_html = html
		super(InputException, self).__init__(msg, help)

	def serialize(self):
		d = {'type': self.__class__.__name__, 'msg': str(self), 'input': self.input_name}
		if self.msg_html:
			d['msg_html'] = self.msg_html
		return d


class InternalException(WebException):
	"""
		Brakuje jakiś danych, coś się źle wczytało itp.
	"""

	def __init__(self, msg, help=None):
		super(InternalException, self).__init__(msg, help)


class AccessException(WebException):
	"""
		Użytkownik nie ma praw, albo coś w tym rodzaju.
	"""
	__slots__ = ('args', 'message', 'help', 'msg_html')

	def __init__(self, profile, msg=None, help=None, html=None):
		# FIXME:
		self.msg_html = html
		if msg:
			super(AccessException, self).__init__(msg, help)
		else:
			super(AccessException, self).__init__(profile, help)


class LogicException(WebException):
	"""
		Operacja nie ma sensu.
	"""
	def __init__(self, msg=None, help=None):
		super(LogicException, self).__init__(msg, help)


class LoginRequiredException(AccessException):
	"""
		Użytkownik musi się zalogować.
	"""
	def __init__(self, msg='Użytkownik musi się zalogować', help=None):
		super(LoginRequiredException, self).__init__(None, msg, help)


class TooLongRequestException(Exception):

	def __init__(self, msg=''):
		super(TooLongRequestException, self).__init__(msg)


class ResponseException(Exception):

	def __init__(self, response, msg='ResponseException'):
		super(ResponseException, self).__init__(msg)
		self.response = response


class InvalidRoute(InternalException):

	def __init__(self, msg=''):
		super(InvalidRoute, self).__init__(msg)


class GeneralException(Exception):

	def __init__(self, msg='GeneralException'):
		super(GeneralException, self).__init__(msg)


class JSONResponse(object):

	def serialize(self):
		raise NotImplementedError()

	def response(self, status=502):

		response = HttpResponse(json.dumps(self.serialize()).encode('utf-8'), content_type='application/json')

		#response["Content-Type"] = "application/json"
		response["Cache-Control"] = "no-store"
		response["Pragma"] = "no-cache"

		return response


class AuthException(WebException, JSONResponse):

	def __init__(self, error, description):
		super(AuthException, self).__init__(description)
		self.error = error
		self.description = description

	def serialize(self):
		return {
			'error': self.error,
			'error_description': self.description
		}

class BotRequestException(Exception):

	def __init__(self, msg=''):
		super().__init__(msg)

