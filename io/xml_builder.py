# -*- coding: utf-8 -*-



import settings

import logging
import os
import xmlwitch
import gzip
import time

class XMLBuilder(xmlwitch.Builder):

	class Abort(Exception):
		pass
	
	def __init__(self, filepath, **kwargs):
		self.filepath = filepath
		self.mtime = None
		xmlwitch.Builder.__init__(self, **kwargs)
		
	def __enter__(self):
		return self

	def __exit__(self, ex_type, ex_val, tb):

		if ex_type is XMLBuilder.Abort:
			return False

		data = str(self)

		with open(self.filepath+'.tmp', 'w') as f:
			f.write(data)

		dest_filename = '{}.gz'.format(self.filepath)
		with gzip.GzipFile(dest_filename + '.tmp', mode='w', compresslevel=9) as output:
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
