# -*- coding: utf-8 -*-

import time
import logging
import os
import settings
import re
# http://www.user-agents.org/allagents.xml
# http://user-agent-string.info/download/UASparser-for-Python
# http://user-agent-string.info/rpc/get_data.php?key=free&format=ini&download=y

log = logging.getLogger('UserAgents')

bots={}
mobiles_re=[]

def toPythonReg(reg):
	reg_l = reg[1:reg.rfind('/')] # modify the re into python format
	reg_r = reg[reg.rfind('/')+1:]
	flag = 0
	if 's' in reg_r: flag = flag | re.S
	if 'i' in reg_r: flag = flag | re.I
	return re.compile(reg_l,flag)

def Init():
	def _parseIniFile(file):
		data = {}
		current_section = 'unknown'
		section_pat = re.compile(r'^\[(\S+)\]$')
		option_pat = re.compile(r'^(\d+)\[\]\s=\s"(.*)"$')

		#step by line
		for line in file.readlines():
			option = option_pat.findall(line)
			if option: #do something for option
				if int(option[0][0]) in data[current_section]:
					data[current_section][int(option[0][0])].append(option[0][1])
				else:
					data[current_section][int(option[0][0])] = [option[0][1],]
			else:
				section = section_pat.findall(line) #do something for section
				if section:
					current_section = section[0]
					data[current_section] = {}
		return data

	new_bots = {}

	file_name = "%s/data/%s" % ( os.path.dirname(__file__), "uas.ini" )
	data = _parseIniFile(open(file_name, 'r'))
	for key, d in list(data.get('robots', {}).items()):
		new_bots[ d[0] ] = key

	log.info( 'Załadowało %s botów' % (len(new_bots)) )

	mobiles = {}
	for key, d in list(data.get('browser', {}).items()):
		if d[0] == "3":
			mobiles[ key ] = d[1]

	new_mobiles_re = []

	for key, d in list(data.get('browser_reg', {}).items()):
		if int(d[1]) in mobiles:
			new_mobiles_re.append(toPythonReg(d[0]))

	log.info('Załadowało %s przeglądarek komórkowych' % (len(new_mobiles_re)))

	global bots
	global mobiles_re

	bots = frozenset(new_bots)
	mobiles_re = new_mobiles_re

def CheckBot(ip, user_agent):
#	b = time.time()
	x = user_agent in bots
#	e = time.time()
#	print u"Sprawdzenie %.8f" % (e-b)
	return x

def CheckMobile(user_agent):
	#b = time.time()
	try:
		for m in mobiles_re:
			if m.findall(user_agent):
				return True
		return False
	finally:
		#e = time.time()
		#print u"Sprawdzenie %.8f w ilości %s" % (e-b, len(mobiles_re))
		pass
