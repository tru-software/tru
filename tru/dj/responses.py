####################################################################
#                                                                  #
#             Copyright (c) 2010, Tomasz Hławiczka                 #
#                       All Rights Reserved.                       #
#                                                                  #
#             http://www.tru.pl                                    #
#                                                                  #
####################################################################

import os
import stat
import logging
from django.conf import settings
import mimetypes
import json
import hashlib
import base64
import copy
import json
from io import BytesIO

from urllib.parse import urlencode, quote

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden, HttpResponseNotModified, StreamingHttpResponse
from django.utils.http import http_date
from django.views.static import was_modified_since, serve

from ..utils.backtrace import GetTraceback


__all__ = ['ImageResponse', 'NoCacheHttpResponse', 'ResponseJsonSuccess', 'FileInMemory', 'RobotsTxtFactory', 'SendFileResponse', 'RedirectWithJavaScriptResponse']


log = logging.getLogger(__name__)


class ImageResponse(StreamingHttpResponse):

	mimes = {
		'PNG': "image/png",
		'JPEG': "image/jpeg",
		'GIF': "image/gif",
		'WEBP': "image/webp",
	}

	STREAM_CHUNK_SIZE = 4096

	def __init__(self, img, format='PNG', nocache=False):

		if format not in ImageResponse.mimes:
			raise ValueError("Incorrect image format: '%s', choose one of %r" % (format, list(ImageResponse.mimes.keys())))

		if not hasattr(img, 'read'):
			buf = BytesIO()
			img.save(buf, format)
			img = buf
		img.seek(0)
		content = iter(lambda: img.read(self.STREAM_CHUNK_SIZE), b'')

		super(ImageResponse, self).__init__(content, content_type=ImageResponse.mimes[format])
		if nocache:
			self['Cache-Control'] = 'must-revalidate'
			self['Pragma'] = 'no-cache'


class NoCacheHttpResponse(HttpResponse):
	# http://en.wikipedia.org/wiki/List_of_HTTP_headers
	# http://pl2.php.net/header

	def __init__(self, content, last_modify=None, etag=None, content_type='text/html', **kwargs):
		super(NoCacheHttpResponse, self).__init__(content, content_type=content_type, **kwargs)
		# if last_modify:
		# 	self[ 'Last-Modified' ] = str( last_modify )
		if etag is not None:
			self['ETag'] = etag

		# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
		self['Cache-Control'] = 'no-cache, no-store, must-revalidate'
		self['Pragma'] = 'no-cache'

		# self[ 'Expires'       ] = 'Mon, 26 Jul 2007 05:00:00 GMT'
		# self[ 'Last-Modified' ] = 'Mon, 26 Jul 2030 05:00:00 GMT' # datetime.strftime( 'D, d M Y H:i:s' ) + ' GMT'
		# self[ 'Cache-Control' ] = 'post-check=0, pre-check=0'


__success = json.dumps({'success': True}).encode('utf8')


def ResponseJsonSuccess():
	return NoCacheHttpResponse(__success, content_type="application/json")


class FileInMemory:

	content = ''
	last_modifcation = None
	mimetype = ''

	def __init__(self, path, binary=False, always_send=False, reload=False, status=200):
		self.path = path
		self.reload = reload
		self.binary = binary
		self.last_modifcation = os.stat(path)
		self.mimetype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
		self.http_date = http_date(self.last_modifcation[stat.ST_MTIME])
		self.always_send = always_send
		self.crc = None
		self.content = None
		self.status = status

		self.Load()

	def Load(self):
		if self.binary:
			with open(self.path, 'rb') as f:
				self.content = f.read()
		else:
			with open(self.path, 'r') as f:
				self.content = f.read().encode('utf8')

		md5 = hashlib.md5()
		md5.update(self.content)
		self.crc = base64.urlsafe_b64encode(md5.digest()).decode('ascii').rstrip('=').replace('-', '')

	def __call__(self, request, status=None):
		return self.Response(request, status=status)

	def Response(self, request, status=None):

		statobj = self.last_modifcation
		if self.reload is True:
			self.Load()
		elif self.always_send is False:
			# try:
			if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'), statobj[stat.ST_MTIME], len(self.content)):
				return HttpResponseNotModified()
			# except Exception:
			# 	pass

		response = HttpResponse(self.content, status=status or self.status, content_type=self.mimetype)
		response["Last-Modified"] = self.http_date
		response["Content-Length"] = len(self.content)
		response["ETag"] = self.GetCRC()
		return response

	def GetCRC(self):
		return self.crc


class RedirectWithJavaScriptResponse(HttpResponse):

	def __init__(self, url):
		code = """
<script type="text/javascript">
/* <![CDATA[ */
window.location.href = %s;
/* ]]> */
</script>
		""" % (json.dumps(url))

		super(RedirectWithJavaScriptResponse, self).__init__(code)


def SendFileResponse(request, path, nocache=False, download=False, tmp=False, age=300, upload_path=False, static_path=False, content_type=None):

	path = '/' + path.lstrip('/')

	if settings.DEBUG or tmp:

		if upload_path:
			response = serve(request, path, document_root=settings.UPLOAD_DIR)
		elif static_path:
			response = serve(request, path, document_root=settings.BASE_DIR_FRONTEND + '/static')
		else:
			raise ValueError("Jedna z opcji powinna być wybrana: upload_path, static_path")

		if content_type:
			response['Content-Type'] = content_type

		if nocache:
			response['Cache-Control'] = 'no-cache, must-revalidate'
			response['Pragma'] = 'no-cache'
		else:
			response['Cache-Control'] = 'max-age={}'.format(age)

		if download:
			response['Content-Disposition'] = 'attachment; filename="{}"'.format(download)
			# response['Pragma'] = 'no-cache'

		if tmp:
			if upload_path:
				tmp_file = settings.UPLOAD_DIR + path
				log.warn("Removing temporary file: {} for {}".format(tmp_file, request.full_url))
				# TODO: Delayed removing files (via celery)
				os.remove(tmp_file)

		# log.info( "Serverd in {} file {}".format( diff.total_seconds(), path ) )

		return response
	else:

		if not content_type:
			(content_type, encoding) = mimetypes.guess_type(path)

		response = HttpResponse(status=200)

		if content_type:
			response['Content-Type'] = content_type

		if nocache:
			response['Cache-Control'] = 'no-cache, must-revalidate'
			response['Pragma'] = 'no-cache'
		else:
			response['Cache-Control'] = 'max-age={}'.format(age)

		if download:
			response['Content-Disposition'] = 'attachment; filename="{}"'.format(download)
			# response['Pragma'] = 'no-cache'

		if upload_path:
			response['X-Accel-Redirect'] = '/protected-files' + quote(path)
		elif static_path:
			response['X-Accel-Redirect'] = '/protected-static' + quote(path)
		else:
			raise ValueError("Jedna z opcji powinna być wybrana: upload_path, static_path")

		return response


class RobotsTxtFactory:
	content = ''

	def _merge(self, lines):
		n = copy.copy(self)
		n.content += lines
		return n

	def Add(self, user_agent, disallow=None):
		if disallow is not None:
			return self._merge('User-agent: {}\nDisallow: {}\n\n'.format(user_agent, disallow))
		return self

	def Sitemap(self, sitemap):
		return self._merge('Sitemap: {}\n\n'.format(sitemap))

	def Response(self):
		return HttpResponse(self.content, content_type='text/plain')

	def Freeze(self):
		x = FrozenRobotsTxt()
		x.content = self.content
		return x


class FrozenRobotsTxt(RobotsTxtFactory):
	def _merge(self, lines):
		return self


class HttpResponseUnauthorized(HttpResponse):
	status_code = 401
