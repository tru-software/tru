# -*- coding: utf-8 -*-

import time
import os
import imp

# http://detectmobilebrowsers.com/

THIS_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\","/")

mod=None

def Init(data_dir=os.path.join(THIS_DIR, 'data')):
	global mod
	mod = imp.load_source('detectmobilebrowser-data', os.path.join(data_dir, 'detectmobilebrowser.middleware.py.txt'))

def CheckMobile(user_agent):
	#b = time.time()
	try:
		if not mod:
			return False
		if mod.reg_b.search(user_agent):
			return True
		if mod.reg_v.search(user_agent[0:4]):
			return True
		return False
	finally:
		#e = time.time()
		#print u"detectmobilebrowsers: Sprawdzenie %.8f" % (e-b)
		pass
