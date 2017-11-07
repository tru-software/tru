
import logging

class UTF8Formatter(logging.Formatter):

	def format(self, *args, **kwargs):
		r = super(UTF8Formatter, self).format(*args, **kwargs)
		if isinstance(r, str):
			r = r.encode('utf8')
		return r

	def formatTime(self, *args, **kwargs):
		r = super(UTF8Formatter, self).formatTime(*args, **kwargs)
		if isinstance(r, str):
			r = r.encode('utf8')
		return r


# logging.UTF8Formatter = UTF8Formatter
