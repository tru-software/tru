# -*- coding: utf-8 -*-

import logging

log = logging.getLogger(__name__)

import iplists
import useragentswitcher
import user_agent_string
import detectmobilebrowsers

def Init():
	user_agent_string.Init()
	iplists.Init()
	useragentswitcher.Init()
	detectmobilebrowsers.Init()

def CheckBot(ip, ua):
	return iplists.CheckBot(ip, ua)

def CheckMobile(ua):
	if useragentswitcher.CheckMobile(ua):
		return True
	if detectmobilebrowsers.CheckMobile(ua):
		# log.warn(u"Wykryte urządzenie mobilne (detectmobilebrowsers): {}".format(ua))
		return True

	return False
