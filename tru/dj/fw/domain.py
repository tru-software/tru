import logging
import settings
import os
import sys
import types
import copy
import datetime

from .mgr import WebMgr

log = logging.getLogger(__name__)


class DomainMeta(type):

	def __new__(cls, name, bases, d):

		new_class = type.__new__(cls, name, bases, d)
		# new_class._register( new_class )

		return new_class


class Domain(object, metaclass=DomainMeta):

	_instance = None

	def __new__(cls):
		if not cls._instance:
			cls._instance = object.__new__(cls)

		return cls._instance

	def __str__(self):
		return self.__class__.__name__

	def SessionHandler(self, request):
		return None

	def LoginHandler(self, request, app, func):
		return None, None
