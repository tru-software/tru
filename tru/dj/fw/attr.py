from django.db import transaction


class WebAttr(object):

	@staticmethod
	def URL(route, *args, **kwargs):

		from .route import Route

		def _cn(func):
			if isinstance(route, str):
				func._attr_route = Route(route, *args, **kwargs)
			else:
				func._attr_route = route
			return func
		return _cn

	Route = URL

	@staticmethod
	def Ajax(type=None, json=False, html=False, GET=False, POST=False, DELETE=False, PUT=False):
		def _cn(func):
			func._attr_ajax = type
			if json:
				func._attr_ajax = 'json'
			if html:
				func._attr_ajax = 'html'
			func._attr_methods = []
			if GET:
				func._attr_methods.append('GET')
			if PUT:
				func._attr_methods.append('PUT')
			if POST:
				func._attr_methods.append('POST')
			if DELETE:
				func._attr_methods.append('DELETE')
			return func
		return _cn

	@staticmethod
	def LoginRequired(func):
		func._attr_login_required = True
		return func

	@staticmethod
	def Public(func):
		func._attr_public = True
		return func

	@staticmethod
	def NoSession(func):
		func._attr_no_session = True
		return func

	@staticmethod
	def SuppressAccessLog(func):
		func._attr_no_accesslog = True
		return func

	@staticmethod
	def Callback(func):
		func._attr_no_accesslog = True
		return func

	@staticmethod
	def CommitOnSuccess(func):
		return transaction.atomic(func)

	@staticmethod
	def CommitManually(func):
		return transaction.commit_manually(func)
