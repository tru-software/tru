from tru.io.converters import getint
from tru.dj.WebExceptions import AccessException


class AntyDDosLimitExceeded(AccessException):
	pass


class AntyDDos:

	PREFIX = None
	MAX_USER_PER_HOUR = 100
	MAX_TOTAL_PER_HOUR = 100
	MAX_CONTEXT_PER_HOUR = 10
	MAX_IP_PER_DAY = 200
	CONTEXT = None
	ERORR_TITLE = 'Usługa chwilowo niedostępna, prosimy spróbować później'

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		return False

	def GetConnection(self):
		raise NotImplemented()

	def Check(self, request):
		return self._check_activity(self.PREFIX, request)

	def CheckAndRaise(self, request):
		if not self.Check(request):
			raise AntyDDosLimitExceeded(request.user, self.ERORR_TITLE)

	def Hit(self, request, **kwargs):
		return self._mark_activity(self.PREFIX, request, **kwargs)

	def _mark_hit(self, pipe, activity, request, ip, now, today, **kwargs):
		hour = request.CURRENT_TIME.strftime('%y%m%d%H')

		pipe.incr('%s:IP:%s:%s' % (activity, today, ip))
		pipe.expire('%s:IP:%s:%s' % (activity, today, ip), 60 * 60 * 24)

		pipe.incr('%s:TH:%s' % (activity, hour))
		pipe.expire('%s:TH:%s' % (activity, hour), 60 * 60)

		if request.profile:
			pipe.incr('%s:%s:U:%s' % (activity, request.profile.id, hour))
			pipe.expire('%s:%s:U:%s' % (activity, request.profile.id, hour), 60 * 60)

		if self.CONTEXT:
			pipe.incr('%s:C:%s:%s' % (activity, self.CONTEXT, hour))
			pipe.expire('%s:C:%s:%s' % (activity, self.CONTEXT, hour), 60 * 60)

	def _mark_activity(self, activity, request, **kwargs):

		if request.IsBot:
			return False

		now = request.CURRENT_TIME.strftime('%y%m%d%H%M%S')
		today = request.CURRENT_TIME.strftime('%y%m%d')
		ip = request.META['REMOTE_ADDR']

		with self.GetConnection().pipeline() as pipe:
			self._mark_hit(pipe, activity, request, ip, now, today, **kwargs)
			pipe.execute()

		return True

	def _check(self, pipe, activity, request, now, hour, today, ip):

		pipe.get('%s:%s:U:%s' % (activity, request.profile.id if request.profile else 0, hour))
		pipe.get('%s:IP:%s:%s' % (activity, today, ip))
		pipe.get('%s:TH:%s' % (activity, hour))
		pipe.get('%s:C:%s:%s' % (activity, self.CONTEXT or '#', hour))

		results = pipe.execute()
		user_per_hour, ip_today, total_per_hour, context_per_hour = list(map(getint, results[-4:]))

		if request.profile:
			if user_per_hour > self.MAX_USER_PER_HOUR:
				return False

		if ip_today > self.MAX_IP_PER_DAY:
			return False

		if total_per_hour > self.MAX_TOTAL_PER_HOUR:
			return False

		if self.CONTEXT and context_per_hour > self.MAX_CONTEXT_PER_HOUR:
			return False

		return results[:-4]

	def _check_activity(self, activity, request):

		if request.IsBot:
			return False

		now = request.CURRENT_TIME.strftime('%y%m%d%H%M%S')
		hour = request.CURRENT_TIME.strftime('%y%m%d%H')
		today = request.CURRENT_TIME.strftime('%y%m%d')
		ip = request.META['REMOTE_ADDR']

		with self.GetConnection().pipeline() as pipe:
			if self._check(pipe, activity, request, now, hour, today, ip) is False:
				return False

		return True


class AntyDDosContext(AntyDDos):

	# __slots__ = ["request"]

	def __init__(self, request=None):
		self.request = request
		if request:
			self.CheckAndRaise(request)

	def __exit__(self, exc_type, exc_value, traceback):
		if exc_type is None:
			self.Hit(self.request)
		return False
