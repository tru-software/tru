# -*- coding: utf-8 -*-

import logging
import os
import xmlwitch
import gzip
import time

try:
	str_u = str
except NameError:
	str_u = str

class XMLBuilder(xmlwitch.Builder):

	class Abort(Exception):
		pass

	def __init__(self, filepath, **kwargs):
		self.filepath = str(filepath)
		self.mtime = None
		xmlwitch.Builder.__init__(self, **kwargs)

	def __enter__(self):
		return self

	def __exit__(self, ex_type, ex_val, tb):

		if ex_type is XMLBuilder.Abort:
			return False

		data = str_u(self).encode('utf8')

		with open(self.filepath+'.tmp', 'wb') as f:
			f.write(data)

		dest_filename = '{}.gz'.format(self.filepath)
		with gzip.GzipFile(dest_filename + '.tmp', mode='wb', compresslevel=9) as output:
			output.write(data)

		os.rename(self.filepath+'.tmp', self.filepath)
		os.rename(dest_filename+'.tmp', dest_filename)

		if self.mtime is not None:
			#mtime = max(self.mtime, settings.BOOT_TIME)
			mtime = self.mtime
			mtime = time.mktime(mtime.timetuple())
			os.utime(self.filepath, (mtime, mtime))
			os.utime(dest_filename, (mtime, mtime))

	def UpdateLastModifyTime(self, mtime):
		if self.mtime is None or self.mtime < mtime:
			self.mtime = mtime

	def UpdateModifyTime(self, mtime):
		self.mtime = mtime
