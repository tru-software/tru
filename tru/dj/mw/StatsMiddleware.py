# -*- coding: utf-8 -*-

import re
from django.conf import settings
import resource
import time
import logging

from .CatchExceptions import CatchExceptions


class StatsMiddleware:

	_last_max_update = int(time.time())
	_requests_counter = 0
	_requests_counter_total = 0

	_mem_diff = False

	external_log = None
	ru_fields = "ru_utime,ru_stime,ru_maxrss,ru_ixrss,ru_idrss,ru_isrss,ru_minflt,ru_majflt,ru_nswap,ru_inblock,ru_oublock,ru_msgsnd,ru_msgrcv,ru_nsignals,ru_nvcsw,ru_nivcsw".split(",")

	def __init__(self, get_response):
		self.get_response = get_response
		self.log = self.external_log or logging.getLogger(__name__)


	def __call__(self, request):

		proces_begin = time.time()
		request._proces_begin = proces_begin

		stats = self.__class__

		stats._requests_counter_total += 1
		stats._requests_counter += 1

		request._request_id = stats._requests_counter_total

		memory_usage_begin = None
		if stats._mem_diff:
			memory_usage_begin = resource.getrusage(resource.RUSAGE_SELF)

		response = self.get_response(request)

		if memory_usage_begin:
			memory_usage_end = resource.getrusage(resource.RUSAGE_SELF)
			# http://linux.die.net/man/2/getrusage
			if memory_usage_end.ru_maxrss - memory_usage_begin.ru_maxrss > 20*1024:
				log_stats.warn("{}: Memory diff {} -> {} during request {}".format(settings.SERVER_ID, memory_usage_begin.ru_maxrss, memory_usage_end.ru_maxrss, request.full_url))

		diff = time.time() - proces_begin

		if diff >= 20.0:

			self.log.warn("{}: Too long request {} \nURL: {}\nOther requests number: {}\nRU diff: {}\nENDPOINT: {}\nPOST: {}\nMETA: {}\n".format(
					settings.SERVER_ID,
					diff,
					request.full_url,
					stats._requests_counter_total - request._request_id,
					{i: getattr(memory_usage_end, i) - getattr(memory_usage_begin, i) for i in self.ru_fields} if memory_usage_begin else '',
					getattr(request, 'MAIN_ENDPOINT', '<UNKNOWN>'),
					request.POST,
					request.META,
				)
			)

		if settings.DATABASE_SQL_TRACE:
			from django.db import connections
			for connection in (i for i in connections.all() if i.connection and hasattr(i, '_queries_log')):
				connection._queries_log = []

		return response

	@classmethod
	def current_performance(cls):

		now = int(time.time())
		try:
			diff = now - cls._last_max_update
			if diff >= 15.0 or diff == 0:
				return 0.0
			return cls._requests_counter/diff
		finally:
			cls._requests_counter = 0.0
			cls._last_max_update = now
