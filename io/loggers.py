
import logging

class UTF8Formatter(logging.Formatter):

	def format(self, *args, **kwargs):
		r = super(UTF8Formatter, self).format(*args, **kwargs)
		#if isinstance(r, str):
			#r = r.encode('utf8')
		return r

	def formatTime(self, *args, **kwargs):
		r = super(UTF8Formatter, self).formatTime(*args, **kwargs)
		#if isinstance(r, str):
			#r = r.encode('utf8')
		return r

class SysLogHandler(logging.handlers.SysLogHandler):

	def format(self, record):
		msg = super(SysLogHandler, self).format(record)
		if isinstance(msg, bytes):
			return msg.decode('utf8')
		return msg

logging.handlers.SysLogHandler = SysLogHandler
#logging.UTF8Formatter = UTF8Formatter
