#!/bin/bash

cd "$(dirname "$0")"

rm google.txt inktomi.txt lycos.txt msn.txt altavista.txt wisenut.txt askjeeves.txt misc.txt non_engines.txt
wget "http://www.iplists.com/nw/google.txt" \
	"http://www.iplists.com/nw/inktomi.txt" \
	"http://www.iplists.com/nw/lycos.txt" \
	"http://www.iplists.com/nw/msn.txt" \
	"http://www.iplists.com/nw/altavista.txt" \
	"http://www.iplists.com/nw/wisenut.txt" \
	"http://www.iplists.com/nw/askjeeves.txt" \
	"http://www.iplists.com/nw/misc.txt" \
	"http://www.iplists.com/nw/non_engines.txt"

wget -O - http://techpatterns.com/downloads/firefox/useragentswitcher.xml > useragentswitcher.xml
wget -O - http://www.user-agents.org/allagents.xml > allagents.xml
wget -O - http://detectmobilebrowsers.com/download/python > detectmobilebrowser.middleware.py.txt
