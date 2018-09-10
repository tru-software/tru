# -*- coding: utf-8 -*-

"""
http://www.user-agents.org/

Legend:
B = Browser
C = Link-, bookmark-, server- checking
D = Downloading tool
P = Proxy server, web filtering
R = Robot, crawler, spider
S = Spam or bad bot
"""

import time
import os
import re
import xml.etree.ElementTree as ET

THIS_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\","/")

def Init(data_dir=os.path.join(THIS_DIR, 'data')):

	uas = []

	with open(os.path.join(data_dir, 'allagents.xml')) as src:
		tree = ET.iterparse(src)

		for event, elem in tree:
			# print('Processing {e}'.format(e=ET.tostring(elem)))
			for e in elem.findall('user-agent'):
				ua = None
				type = None
				for c in e.getchildren():
					if c.tag == 'String':
						ua = c.text
					elif c.tag == 'Type':
						type = c.text

				if ua and type:

					if 'B' in type:
						continue

					uas.append(hash(ua))

	return uas
