# -*- coding: utf-8 -*-

import time
import os
import re
import array
import bisect
import logging

from netaddr import *

import user_agents

log = logging.getLogger('UserAgents')

# http://www.iplists.com/nw/

THIS_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\","/")

ips = [None, None, None, None]
for i in range(4):
	ips[i] = array.array("I")
ua = array.array("l")

def Init(data_dir=os.path.join(THIS_DIR, 'data')):
	global ips
	global ua
	ips, ua = ImportDir(data_dir)

def index(a, x):
	i = bisect.bisect_left(a, x)
	return i != len(a) and a[i] == x

def CheckBot(ip, user_agent):
#	b = time.time()

	nums = ip.split('.')
	ip_int = int(nums[0]) << 24 + int(nums[1]) << 16 + int(nums[2]) << 8 + int(nums[3]);

	if index(ips[2], ip_int & 0xffffff00):
#		print ":1 %s %s"% (x, hex(ips[2][x]))
		return True

	if index(ips[3], ip_int):
#		print ":2 %s %s"% (x, hex(ips[3][x]))
		return True

	if index(ua, hash(user_agent)):
		return True

#	e = time.time()
#	print u"Sprawdzenie %.8f" % (e-b)
	return False

def CheckMobile(user_agent):
#	for m in mobiles_re:
#		if m.findall(user_agent):
#			return True
	return False

def ImportDir(data_dir):

	all_ips = [None, None, None, None]
	for i in range(4):
		all_ips[i] = array.array('I')

	all_ua = array.array('l')

	all_ua.extend(user_agents.Init(data_dir))

	for filename in os.listdir(data_dir):

		if not filename.endswith('.txt'):
			continue

		ips, ua = ImportFile(os.path.join(data_dir, filename))

		for i in range(4):
			all_ips[i].extend(ips[i])

		all_ua.extend(ua)

	for i in range(4):
		all_ips[i] = sorted(all_ips[i])

	all_ua = sorted(all_ua)
	
	log.info('iplists: Załadowało %s adresów IP botów' % (sum(map(len,all_ips))))
	log.info('iplists: Załadowało %s User-Agents botów' % (len(all_ua)))

	return all_ips, all_ua


def ImportFile(filepath):

	ips = [ [], [], [], [] ]

#	ips[2].append(IPNetwork('127.0.0').value)
#	ips[3].append(IPNetwork('127.0.0.1').value)

	ua = []
	with open(filepath, 'r') as f:

		for line in f.readlines():

			line = line.strip()

			if not line:
				continue

			if line.startswith('# UA '):
				# print hash(line[6:-1]), line[6:-1]
				ua.append(hash(line[6:-1]))
			elif line.startswith('#'):
				continue
			else:
				try:
					ips[ line.count(".") ].append(IPNetwork(line).value)
				except:
					#FIXME: podawany jest czasem host zamiast IP, albo IP się zmienia.
					#print "cannot add ip {}".format(line)
					pass

	return ips, ua