from django.http import HttpRequest
import settings
import sys
import time
import logging
import os
import random
import datetime

from django.utils.cache import patch_vary_headers
from django.utils.http import cookie_date
from django.contrib.sessions.backends.base import SessionBase, CreateError, VALID_KEY_CHARS
from django.core.exceptions import SuspiciousOperation, ObjectDoesNotExist

from tru.utils.backtrace import GetTraceback
from .CatchExceptions import CatchExceptions


import datamodel

# Use the system (hardware-based) random number generator if it exists.
# randrange = random.SystemRandom().randrange if hasattr(random, 'SystemRandom') else random.randrange
# MAX_SESSION_KEY = 18446744073709551616     # 2 << 63

# ------------------------------------------------------------------------

log = logging.getLogger(__name__)

# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------


class SessionStore(SessionBase):

	def __init__(self, request, key_name, domain=None, secure=False, expires=None):

		session_key = request.COOKIES.get(key_name, None)

		if not session_key or len(session_key) != 32 or sum(1 if i in VALID_KEY_CHARS else 0 for i in session_key) != len(session_key):
			if session_key:
				log.error("Incorrect session key '%s'. (%s, %s)" % (session_key, request.META.get('REMOTE_ADDR', ''), request.META.get('HTTP_USER_AGENT', '')))
			session_key = None

		super(SessionStore, self).__init__(session_key)

		self.key_name = key_name
		self.secure = secure if settings.ENABLE_SSL else False
		# self.request = request
		self.expires = datetime.timedelta(seconds=expires) if expires else None
		self.domain = domain

		self.user = None

		if self.key_name:
			self.load()

	# ------------------------------------------------------------------------

	@property
	def cache_key(self):
		return self._get_or_create_session_key()

	def encode(self, session_dict):
		"Returns the given session dictionary serialized and encoded as a string."
		return self.serializer().dumps(session_dict)

	def decode(self, session_data):
		try:
			return self.serializer().loads(session_data)
		except Exception as ex:
			log.warn("Invalid session {} data: {}: {}".format(self._session_key, session_data, ex))
			return {}

	def load(self):

		self.user = None

		session_data = datamodel.RedisSession().Load(self.cache_key, self.expires)

		if session_data is None:
			self.create()
			return {}

		session_data = self.decode(session_data)

		if session_data.get('user'):
			self.user = datamodel.UserPartial(data=session_data['user'])
			self.user.config = datamodel.UsersSettings().GetUserConfig(self.user.id)

		return session_data

	def create(self, user=None):

		self.user = None
		self._session_key = self._get_new_session_key()
		try:
			if user is not None:
				self.user = datamodel.UserPartial(user=user)
				self['user'] = self.user.Serialize()

			self.save(must_create=True)
		except CreateError:
			pass
		self.modified = True

	def save(self, must_create=False):
		if must_create:
			result = datamodel.RedisSession().Create(self.cache_key, self.encode(self._get_session(no_load=must_create)), self.expires)
		else:
			result = datamodel.RedisSession().Update(self.cache_key, self.encode(self._get_session(no_load=must_create)), self.expires)
		if must_create and not result:
			raise CreateError

	def exists(self, session_key):
		return datamodel.RedisSession().Exists(session_key)

	def delete(self, session_key=None):
		if session_key is None:
			if self.session_key is None:
				return
			session_key = self.session_key
		datamodel.RedisSession().Delete(session_key)

	@classmethod
	def clear_expired(cls):
		pass

	def get_user(self):
		return self.user

	def add_to_response(self, response):

		if not self.key_name:
			return

		if self.accessed:
			patch_vary_headers(response, ('Cookie',))

		if self.modified:
			self.save()

		if self.modified:
			now = int(time.time())
			if self.expires is None:
				max_age = None
				expires = None
			else:
				max_age = self.expires.total_seconds()
				expires = cookie_date(now + max_age)

			response.set_cookie(self.key_name, self.session_key, max_age=7 * 24 * 60 * 60, expires=cookie_date(7 * 24 * 60 * 60 + now), domain=self.domain, path='/', secure=self.secure or None)

# ------------------------------------------------------------------------


class LazyUser(object):
	def __get__(self, request, obj_type=None):
		if not hasattr(request, '_cached_user'):
			request._cached_user = request.session.get_user()
		return request._cached_user


HttpRequest.user = LazyUser()

# ------------------------------------------------------------------------


def SessionMiddleware(get_response):

	session_name = 'foto_sid'
	timeout = 60 * 60
	timeout_internal = 24 * 60 * 60

	@CatchExceptions
	def process_request(request):

		expires = timeout_internal if request.META.get('INTERNAL_ADDR') else timeout

		try:
			ctrl_instance = request.original_route.GetApplication(request)
			method_name = request.original_route.GetMethod(request)

			func = ctrl_instance._find_action(request, method_name)
			if getattr(func, '_attr_no_session', False) is not True:
				request.session = SessionStore(request, session_name, expires=expires)
			else:
				request.session = SessionStore(request, None)

		except Exception as ex:
			log.error("Cannot initialize session:\n%s" % (GetTraceback(ex, request=request)))

		response = get_response(request)

		try:
			if hasattr(request, 'session'):
				if request.session.expires is not None and getattr(request, 'IsBot', False) is False:
					request.session.add_to_response(response)
				del request.session
		except Exception as ex:
			log.error("Cannot store session to response:\n%s" % (GetTraceback(ex, request=request)))

		return response

	return process_request

# ------------------------------------------------------------------------
