# -*- coding: utf-8 -*-

import os
import gc
import sys
import traceback
import threading
import datetime
from django.conf import settings
import pickle
import logging
from functools import wraps

log = logging.getLogger(__name__)


def _make_str(x):
	return x if isinstance(x, str) else x.decode('UTF8')

def FormatTraceback():
	return ''.join(map(_make_str, traceback.format_exception(*sys.exc_info())))

def GetTraceback(exception=None, request=None):
	r = '';

	if request is None:
		request = GetTraceback.GetRequest()

	if request is not None:
		environ = request.environ if hasattr(request, 'environ') else {}
		profile = request._cached_profile if hasattr(request, '_cached_profile') else None
		META = request.META if hasattr(request, 'META') else {}
		COOKIES = request.COOKIES if hasattr(request, 'COOKIES') else {}

		r += 'URL: %s\nUSER_AGENT: %s\nUSER: %s\nREMOTE_ADDR: %s\nCURRENT_ENDPOINT: %s\nMETHOD: %s\nCOOKIES: %s\n' % (
			request.full_url,
			META.get('HTTP_USER_AGENT', 'NONE'),
			profile,
			META.get('REMOTE_ADDR', 'NONE'),
			getattr(request, 'CURRENT_ENDPOINT', None),
			getattr(request, 'method', None),
			COOKIES
		)

	r += 'PID: {} ({})\n'.format(os.getpid(), settings.SERVER_ID)
	r += FormatTraceback()
	return r

GetTraceback.GetRequest = lambda: None

# ----------------------------------------------------------------------------

def FindThreads():

	frames = sys._current_frames()
	# threads = sorted( frames.items(), key=lambda x: x[0] )
	threads_summary = [ReadStack(thread_id, frame) for thread_id, frame in list(frames.items())]
	return threads_summary

# ----------------------------------------------------------------------------

def ReadStack(thread_id, frame):
	now = datetime.datetime.now()
	f = frame
	request = None
	connection = None
	while f is not None:
		filename = f.f_code.co_filename
		function = f.f_code.co_name
		lineno = f.f_lineno - 1
		# loader = frame.f_globals.get('__loader__')
		module_name = f.f_globals.get('__name__')

		if function == 'process_request':
			vars = f.f_locals
			request = vars.get('request', None)
			connection = vars.get('CURRENT_CONNECTION', None)

		f = f.f_back

	where = "%s:%s %s()" % (frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)

	if request is not None:
		CURRENT_TIME = getattr(request, 'CURRENT_TIME', None)
		if isinstance(CURRENT_TIME, datetime.datetime):
			diff = now - CURRENT_TIME
			return [frame, thread_id, diff.seconds + diff.days*60*60*24, where, request, connection]
	else:
		return [frame, thread_id, 0, where, request, connection]

"""
import gc
import traceback
from greenlet import greenlet

for ob in gc.get_objects():
 if isinstance(ob, greenlet) and ob:
  print ''.join(traceback.format_stack(ob.gr_frame))

"""

def DumpThreads_gevent(sig=None, frame=None):

	import gc
	import traceback
	from greenlet import greenlet

	try:
		pid = os.getpid()
		logfile = None

		if settings.DEBUG:
			log = lambda x: sys.stdout.write(x + "\n")
		else:
			logfile = open(settings.BASE_DIR + ('/../logs/current/backtrace.%d' % (pid)), "a" )
			log = lambda x: logfile.write(x + "\n")

		now = datetime.datetime.now()

		threads_summary = []
		for ob in gc.get_objects():
			if isinstance(ob, greenlet) and ob and ob.gr_frame is not None:
				threads_summary.append(ReadStack(id(ob), ob.gr_frame))

		threads_summary.sort(key=lambda x: x[2])
		threads_summary.reverse()


		for frame, thread_id, started, where, request, conn in threads_summary:
			if request is None:
				log("%d %d %d %s" % (pid, thread_id, started, where))
			else:

				full_url = 'http://%s%s' % ( request.environ.get('HTTP_HOST','<HOST>'), request.environ.get('PATH_INFO','<PATH>') )
				if request.environ.get('QUERY_STRING', None):
					full_url += '?' + request.environ['QUERY_STRING']

				endpoint = getattr(request, 'CURRENT_ENDPOINT', '[unknown]')

				log("%d %d %d %s %s %s" % (pid, thread_id, started, where, full_url, endpoint))

		log("")
		log("Threads details:")

		for frame, thread_id, started, where, request, conn in threads_summary:

			log("THREAD      : %s" % (thread_id))

			if request is not None:
				
				full_url = 'http://%s%s' % ( request.environ.get('HTTP_HOST','<HOST>'), request.environ.get('PATH_INFO','<PATH>') )
				if request.environ.get('QUERY_STRING', None):
					full_url += '?' + request.environ['QUERY_STRING']

				endpoint = getattr(request, 'CURRENT_ENDPOINT', '[unknown]')

				CURRENT_TIME = getattr(request, 'CURRENT_TIME', None)
				if CURRENT_TIME:
					log("  BEGIN      : %s %s" % (request.CURRENT_TIME, (now - CURRENT_TIME).seconds))
				log("  HTTP QUERY : %s" % (full_url))
				log("  ENDPOINT   : %s" % (endpoint))
				log("  POST       : %s" % (request.POST))
				log("  COOKIES    : %s" % (request.COOKIES))
				log("  SESSION    : %s" % (request.session._session_key if hasattr(request, 'session') else '[none]'))
				log("  PROFILE    : %s" % (request.profile if getattr(request, 'profile', None) != None else '[none]'))
				log("  REQUEST    : %s" % (request) )

			if conn is not None:

				log("  DATABASE QUERIES:")
				for query in conn.queries:
					log("    %s" % (query))
				log("---")

			log("")

			f = frame
			while f is not None:
				filename = f.f_code.co_filename
				function = f.f_code.co_name
				lineno = f.f_lineno - 1
				# loader = frame.f_globals.get('__loader__')
				module_name = f.f_globals.get('__name__')

				where = "%s:%s %s()" % (f.f_code.co_filename, f.f_lineno, f.f_code.co_name)
				
				log("  %s" % (where))

				if function != 'DumpThreads_gevent':
					for name, var in list(f.f_locals.items()):
						if name not in ('__builtins__', 'self', 'request'):
							try:
								log("    %s=%r" % (name, var))
							except Exception as ex:
								log("    %s=%s" % (name, "cannot read value!"))
				log("")

				f = f.f_back

			log("")

		if logfile:
			logfile.close()
	except Exception as ex:
		print((GetTraceback(ex)))

def DumpThreads(sig, frame):

	try:
		pid = os.getpid()
		logfile = None

		if settings.DEBUG:
			log = lambda x: sys.stdout.write(x + "\n")
		else:
			logfile = open(settings.BASE_DIR + ('/../logs/current/backtrace.%d' % (pid)), "a" )
			log = lambda x: logfile.write(x + "\n")

		now = datetime.datetime.now()

		threads_summary = FindThreads()

		threads_summary.sort(key=lambda x: x[2])
		threads_summary.reverse()

		log("Threads summary:")

		for frame, thread_id, started, where, request, conn in threads_summary:
			if request == None:
				log("%d %d %d %s" % (pid, thread_id, started, where))
			else:

				full_url = 'http://%s%s' % ( request.environ.get('HTTP_HOST','<HOST>'), request.environ.get('PATH_INFO','<PATH>') )
				if request.environ.get('QUERY_STRING', None):
					full_url += '?' + request.environ['QUERY_STRING']

				endpoint = getattr(request, 'CURRENT_ENDPOINT', '[unknown]')

				log("%d %d %d %s %s %s" % (pid, thread_id, started, where, full_url, endpoint))

		log("")
		log("Threads details:")

		for frame, thread_id, started, where, request, conn in threads_summary:

			log("THREAD      : %s" % (thread_id))

			if request != None:
				
				full_url = 'http://%s%s' % ( request.environ.get('HTTP_HOST','<HOST>'), request.environ.get('PATH_INFO','<PATH>') )
				if request.environ.get('QUERY_STRING', None):
					full_url += '?' + request.environ['QUERY_STRING']

				endpoint = getattr(request, 'CURRENT_ENDPOINT', '[unknown]')

				CURRENT_TIME = getattr(request, 'CURRENT_TIME', None)
				if CURRENT_TIME:
					log("  BEGIN      : %s %s" % (request.CURRENT_TIME, (now - CURRENT_TIME).seconds))
				log("  HTTP QUERY : %s" % (full_url))
				log("  ENDPOINT   : %s" % (endpoint))
				log("  POST       : %s" % (request.POST))
				log("  COOKIES    : %s" % (request.COOKIES))
				log("  SESSION    : %s" % (request.session._session_key if hasattr(request, 'session') else '[none]'))
				log("  PROFILE    : %s" % (request.profile if getattr(request, 'profile', None) != None else '[none]'))
				log("  REQUEST    : %s" % (request) )

			if conn != None:

				log("  DATABASE QUERIES:")
				for query in conn.queries:
					log("    %s" % (query))
				log("---")

			log("")

			f = frame
			while f != None:
				filename = f.f_code.co_filename
				function = f.f_code.co_name
				lineno = f.f_lineno - 1
				# loader = frame.f_globals.get('__loader__')
				module_name = f.f_globals.get('__name__')

				where = "%s:%s %s()" % (f.f_code.co_filename, f.f_lineno, f.f_code.co_name)
				
				log("  %s" % (where))

				if function != 'DumpThreads':
					for name, var in list(f.f_locals.items()):
						if name not in ('__builtins__', 'self', 'request'):
							try:
								log("    %s=%r" % (name, var))
							except Exception as ex:
								log("    %s=%s" % (name, "cannot read value!"))
				log("")

				f = f.f_back

			log("")

		if logfile:
			logfile.close()
	except Exception as ex:
		print((GetTraceback(ex)))

# ----------------------------------------------------------------------------

def DumpMemory(sig, frame):

	try:
		
		logfile = None

		if settings.DEBUG:
			log = lambda x: sys.stdout.write(x + "\n")
		else:
			pid = os.getpid()
			logfile = open(settings.BASE_DIR + ('/../logs/current/memtrace.%d' % (pid)), "a" )
			log = lambda x: logfile.write(x + "\n")

		#import objgraph
		#from wre import FW
		#objgraph.show_refs(FW.WebMgr, filename='sample-graph.png')
		#objgraph.show_most_common_types()

		from guppy import hpy
		
		hp = hpy()
		# hp.setrelheap()
		h = hp.heap()
		print((h.bytype))
		# log( h.heap() )

		if logfile:
			logfile.close()

	except Exception as ex:
		print((GetTraceback(ex)))

# ----------------------------------------------------------------------------

def DumpMemory2(sig, frame):

	try:
		pid = os.getpid()
		with open(settings.BASE_DIR + ('/../logs/current/memdump.%d' % (pid)), "w" ) as logfile:
			for obj in gc.get_objects():
				i = id(obj)
				size = sys.getsizeof(obj, 0)
				#    referrers = [id(o) for o in gc.get_referrers(obj) if hasattr(o, '__class__')]
				referents = [id(o) for o in gc.get_referents(obj)]
				if hasattr(obj, '__class__'):
					cls = str(obj.__class__)
					pickle.dump({'id': i, 'class': cls, 'size': size, 'referents': referents}, logfile)
				else:
					pickle.dump({'id': i, 'class': type(obj).__name__, 'value': repr(obj), 'size': size, 'referents': referents}, logfile)
	except Exception as ex:
		print((GetTraceback(ex)))

# ----------------------------------------------------------------------------

old_objects = set()

def DumpBigObjects(sig, frame):
	import gc, heapq, sys, collections

	gc.collect()

	log.warn("GC: count:{} garbage:{} objects:{}".format(sum(gc.get_count()), len(gc.garbage), len(gc.get_objects())))

#	for i in heapq.nlargest(100, gc.get_objects(), lambda x: sys.getsizeof(x)):
#		log.warn(u"GC: largest object: {}: {} {}..".format(sys.getsizeof(i), type(i), repr(i)[:50]))


	first_time = len(old_objects) == 0

#	types = collections.defaultdict(int)
	for i in gc.get_objects():
#		types[type(i)] += 1

		if isinstance(i, (list, dict)):
			_id = id(i)
			if _id not in old_objects:
				old_objects.add(_id)
				if not first_time:
					try:
						log.warn("GC: list-or-dict: {} {}".format(_id, i))
						log.warn("GC: referrers: {}".format(list(map(str, gc.get_referrers(i)))))
					except Exception as ex:
						log.warn("GC: error: {}".format(ex))
						raise
	
#	for k, v in heapq.nlargest(100, types.items(), lambda x: x[1]):
#		log.warn(u"GC: most used type: {}: {}".format(v, k))

# ----------------------------------------------------------------------------

def CatchAll(log):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as ex:
				log.error("Zrzut błędu\n{}".format(GetTraceback(ex)))
			return None

		return wrapper
	return decorator

# -------------------------------------------------------------------------------

def GetClassPath(cls):
    if isinstance(cls, type):
        return "%s.%s"%(cls.__module__,cls.__name__)
    return "%s.%s"%(cls.__module__,cls.__class__.__name__)

# -------------------------------------------------------------------------------
