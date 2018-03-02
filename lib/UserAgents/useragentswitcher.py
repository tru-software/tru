# -*- coding: utf-8 -*-

"""
http://techpatterns.com/downloads/firefox/useragentswitcher.xml

"""

import time
import os
import logging
import array
import xml.etree.ElementTree as ET
from .iplists import index

log = logging.getLogger('UserAgents')

THIS_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\","/")

all_uas = array.array("l")

def Init(data_dir=os.path.join(THIS_DIR, 'data')):

	global all_uas
	uas = []

	with open(os.path.join(data_dir, 'useragentswitcher.xml')) as src:
		tree = ET.iterparse(src)

		for event, elem in tree:
			for e in elem.findall("folder[@description='Mobile Devices']"):
				for d in e.iter("useragent"):
					uas.append(hash(d.get('useragent')))

	uas.sort()
	all_uas.extend(uas)

	log.info('useragentswitcher: Załadowało %s User-Agents smartphonów' % (len(all_uas)))

	return uas


def CheckMobile(user_agent):
	return index(all_uas, hash(user_agent))

