# -*- coding: utf-8 -*-

import types
import logging

from .exceptions import InternalException

log    = logging.getLogger(__name__)

# -------------------------------------------------------------------------------------------

class MobileInterface(object):

	def GetPublicName(self):
		return self.__class__.__name__

	# -------------------------------------------------------------------------------------------

	def __str__(self):
		return 'MobileInterface %s %s' % (self.__class__, id(self))

# -------------------------------------------------------------------------------------------

class MobileAPI(object):

	# -------------------------------------------------------------------------------------------

	def __init__(self, version):
		self.version = version
		self.interfaces = {}
		self.all_methods = {}

	# -------------------------------------------------------------------------------------------

	def RegisterInterface(self, iface_object):

		if not isinstance(iface_object , MobileInterface):
			raise InternalException("Cannot register interface %s. Interface class need to be based on %s class." % (iface_object, MobileInterface))

		name = iface_object.GetPublicName()

		if name in self.interfaces:
			raise InternalException("Interface %s is already registred to API %s." % (iface_object, self))

		self.interfaces[ name ] = iface_object

		for member_name in dir(iface_object):
			func = getattr(iface_object, member_name)
			if member_name.startswith('__') and member_name.endswith('__'):
				continue
			if not isinstance(func, types.FunctionType) and not isinstance(func, types.MethodType):
				continue
			if getattr(func, 'public', False) != True:
				continue

			self.all_methods[ '%s.%s' % (name, member_name) ] = func

	# -------------------------------------------------------------------------------------------

	def FindMethod(self, interface, method):
		return self.all_methods.get('%s.%s' % (interface, method), None)

	# -------------------------------------------------------------------------------------------

	def __str__(self):
		return 'MobileAPI %s' % (self.version)

# -------------------------------------------------------------------------------------------
