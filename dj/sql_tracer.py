# -*- coding: utf-8 -*-

import time
import traceback
import logging

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper

log = logging.getLogger(__name__)

class GlobalQueriesCounter(object):
	index = 0

class CursorDebugWrapperWithBacktrace(CursorWrapper):

	__slots__ = (
		'__print_on_console',
		'cursor',
	)

	WebMgr = None

	def __init__(self, cursor, db, print_on_console):
		super(CursorDebugWrapperWithBacktrace, self).__init__(cursor, db)
		self.__print_on_console = print_on_console

	def execute(self, sql, params=()):
		start = time.time()
		try:
			return self.cursor.execute(sql, params)
		finally:
			stop = time.time()
			diff = (stop - start)
			self.WebMgr.Local.OnDBCall(1, diff)

			if diff >= 2.0:
				if self.WebMgr.Local.request:
					endpoint = getattr(self.WebMgr.Local.request, 'CURRENT_ENDPOINT', '<unknown>')
					full_url = getattr(self.WebMgr.Local.request, 'full_url', '<unknown>')
				else:
					endpoint, full_url = '', ''
				log.warn("Heavy ({}) SQL: {} z {} ({})".format(diff, self.cursor.query, full_url, endpoint))

			if self.WebMgr.Local.sql_trace:
				if self.__print_on_console:
					GlobalQueriesCounter.index += 1
					print(("\033[93m%d\033[0m. \033[94m%s\033[0m \033[93m%s\033[0m" % (GlobalQueriesCounter.index, getattr(self.WebMgr.Local.request, 'CURRENT_ENDPOINT', '<unknown>'), stop - start)))
					#print "\033[92m%s\033[0m %s" % (sql, params)
					print(("\033[92m%s\033[0m" % (self.cursor.query, )))
					if self.WebMgr.Local.sql_trace >= 2: # and self.WebMgr.current_web_environ is not None:
						print("")
						print((''.join(self.bt())))
						print("")
				else:
					#sql = self.db.ops.last_executed_query(self.cursor, sql, params)
					if not hasattr(self.db, '_wre_queries_log'):
						self.db._wre_queries_log = []

					sql = self.cursor.query
					self.db._wre_queries_log.append({
						'sql': sql,
						'time': "%.3f" % (stop - start),
						'bt': self.bt(),
						'part': getattr(self.WebMgr.Local.request, 'CURRENT_ENDPOINT', '<unknown>')
					})

	def executemany(self, sql, param_list):
		start = time.time()
		try:
			return self.cursor.executemany(sql, param_list)
		finally:
			stop = time.time()
			diff = (stop - start)
			self.WebMgr.Local.OnDBCall(len(param_list), diff)

			if diff >= 2.0:
				if self.WebMgr.Local.request:
					endpoint = getattr(self.WebMgr.Local.request, 'CURRENT_ENDPOINT', '<unknown>')
					full_url = getattr(self.WebMgr.Local.request, 'full_url', '<unknown>')
				else:
					endpoint, full_url = '', ''
				log.warn("Bardzo ciężkie ({}) zapytanie SQL: {} {} z {} ({})".format(diff, sql, param_list, full_url, endpoint))

			if self.WebMgr.Local.sql_trace:
				if self.__print_on_console:
					GlobalQueriesCounter.index += 1
					print(("\033[93m%d\033[0m. \033[94m%s\033[0m \033[93m%s\033[0m" % (GlobalQueriesCounter.index, getattr(self.WebMgr.Local.request, 'CURRENT_ENDPOINT', '<unknown>'), stop - start)))
					print(("\033[92m%s\033[0m %s" % (sql, param_list)))
					if self.WebMgr.Local.sql_trace >= 2: # and self.WebMgr.current_web_environ != None:
						print("")
						print((''.join(self.bt())))
						print("")
				else:
					if not hasattr(self.db, '_wre_queries_log'):
						self.db._wre_queries_log = []

					self.db.db._wre_queries_log.append({
						'sql': '%s times: %s' % (len(param_list), sql),
						'time': "%.3f" % (stop - start),
						'bt': self.bt(),
						'part': getattr(self.WebMgr.Local.request, 'CURRENT_ENDPOINT', '<unknown>')
					})

	def bt(self):
		b = list(traceback.format_stack())[:-2]
		r = []
		for i in b:
			if r:
				r.append(i)
			elif 'wre/lib/middleware/' in i:
				r.append(i)
		return r or b

def install(print_on_console, mgr):

	import django
	CursorDebugWrapperWithBacktrace.WebMgr = mgr

	# django.VERSION = (1, 11, 3, u'alpha', 0)
	if django.VERSION >= (1, 11, 0):
		def make_cursor(self, cursor):
			return CursorDebugWrapperWithBacktrace(cursor, self, print_on_console)
	else:
		def make_cursor(self, *args, **kwargs):
			return CursorDebugWrapperWithBacktrace(self._cursor(), self, print_on_console)

	BaseDatabaseWrapper.make_cursor = make_cursor
	setattr(BaseDatabaseWrapper, 'queries_logged', False)
