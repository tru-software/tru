import os
import datetime
import magic
import logging
import io
import uuid
import urllib.parse

from PIL import Image
from tru.io import converters
from tru.fs.utils import FileNameExtension
from tru.dj.WebExceptions import InputException, WebException


from django.conf import settings
from django.db import models


log = logging.getLogger(__name__)


class FileType:

	def __init__(self, mimetype, exts):
		_ = lambda x: '.'+x
		self.mimetype = mimetype if isinstance(mimetype, (list, tuple)) else (mimetype, )
		self.exts = tuple(map(_, exts))


class FileMgr:

	AntyDDosClass = None

	class FileExts:
		AUDIO = FileType('audio/', ('mp3', 'wav', 'm4a', 'mid', 'mpa', 'ra', 'wma', 'ogg'))
		IMAGE = FileType('image/', ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'mpo'))
		VIDEO = FileType('video/', ('avi', 'flv', 'wmv', 'mp4', 'mov', 'ogv', 'm4v', 'mpg', 'mp2', 'mpeg', 'mpe', 'mpv'))
		EXCEL = FileType(('application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/octet-stream', 'application/vnd.ms-office', 'application/vnd.oasis.opendocument.spreadsheet'), ('xls', 'xlsx', 'odt'))
		WORD  = FileType(('application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.oasis.opendocument.text'), ('doc', 'docx', 'ods'))
		PPT   = FileType(('application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.oasis.opendocument.presentation'), ('pps', 'ppsx', 'odp'))
		PDF   = FileType('application/pdf', ('pdf', ))
		XML   = FileType(('application/xml','text/xml'), ('xml', ))

	ALLOWED_TYPES = [FileExts.IMAGE, FileExts.AUDIO]
	ALLOWED_IMAGE_FORMATS = dict(JPEG='.jpg', PNG='.png', GIF='.gif', BMP='.bmp', MPO='.jpeg')
	FILE_UPLOAD_MAX_SIZE = settings.FILE_UPLOAD_MAX_MEMORY_SIZE
	UPLOAD_DIR = settings.UPLOAD_DIR
	NAMESPACE = "uploads-tmp"

	def IsValidExtension(self, fileName):
		for i in self.ALLOWED_TYPES:
			if FileNameExtension(fileName).lower() in i.exts:
				return True
		return False

	def FetchFile(self, request):

		if request.META['CONTENT_TYPE'].startswith('multipart/form-data'):
			if 'upload' in request.FILES:
				f = request.FILES['upload']
				fileName = f.name
				fileSize = f.size
				# f.content_type
				data = f.read(fileSize)
			if 'HTTP_X_FILE_NAME' in request.META:
				fileName = request.META["HTTP_X_FILE_NAME"]
				fileSize = int(request.META["CONTENT_LENGTH"])
				data = request.read(fileSize)
		elif request.META['CONTENT_TYPE'] == 'application/octet-stream':
			fileName = urllib.parse.unquote(request.META["HTTP_X_FILE_NAME"])
			fileSize = int(request.META["CONTENT_LENGTH"])
			data = request.read(fileSize)
		elif 'qqfile' in request.FILES:
			fileName = request.FILES['qqfile'].name
			data = request.FILES['qqfile'].read()
			fileSize = len(data)
		else:
			fileName = ''

		if fileSize > self.FILE_UPLOAD_MAX_SIZE:
			raise InputException('file', 'Plik jest zbyt duży')

		return self.CheckFileType(fileName, data)

	@classmethod
	def GetImageMeta(cls, stream):

		im = stream if Image.isImageType(stream) else Image.open(stream)

		# http://effbot.org/imagingbook/image.htm#tag-Image.Image.verify
		im.load()

		return {
			'format': im.format,
			'width': im.width,
			'height': im.height,
			'mode': im.mode  # https://pillow.readthedocs.io/en/3.1.x/handbook/concepts.html#concept-modes
		}

	def GetFileMeta(self, mimetype, data):

		im = None
		meta = {}
		if mimetype.startswith('image/'):
			meta = self.GetImageMeta(Image.open(io.BytesIO(data)))

			if meta['format'] not in self.ALLOWED_IMAGE_FORMATS:
				log.error("Unsupported image format: %s" % (im.format))
				raise InputException('file', 'Format obrazu "{}" nie jest wspierany'.format(im.format))

		# Dodatkowe testy na poprawność pliku/danych

		meta['size'] = len(data)
		return meta, im

	def CheckFileType(self, fileName, data):

		if not self.IsValidExtension(fileName):
			raise InputException('file', 'Plik posiada nieprawidłowe rozszerzenie')

		mimetype = magic.from_buffer(data, mime=True) or 'unknown'

		for i in self.ALLOWED_TYPES:
			if mimetype.startswith(i.mimetype):
				break
		else:
			raise InputException('file', f'Plik typu "{mimetype}" nie został rozpoznany jako jeden z wspieranych')

		try:
			meta, im = self.GetFileMeta(mimetype, data)
			return data, meta.get('format') or FileNameExtension(fileName).lower(), fileName, mimetype, im
		except WebException as ex:
			raise
		except Exception as ex:
			log.error("Cannot open image file (size=%s): %s" % (len(data), ex))
			raise InputException('file', 'Plik nie został rozpoznany jako prawidłowy obraz')

	def GetFilesSpaceLimit(self, request):
		return None

	def GetUsedFilesSpace(self, request):
		return None

	def GetDirNameInt(self, request):
		return 'src/{}'.format(datetime.datetime.now().strftime('%y/%m/%d'))

	# Ta funkcja może być nadpisana, aby zwracała inną ścieżkę dla developerskiego środowiska
	def GetDirName(self, request):
		return self.NAMESPACE + '/' + self.GetDirNameInt(request)

	def EnsureExist(self, dest_dir):
		if os.path.isdir(dest_dir) is False:
			os.makedirs(dest_dir, exist_ok=True)

	def GetNewFileName(self, request, orgFileName, ext):
		dest_dir = self.GetDirName(request)
		self.EnsureExist(self.UPLOAD_DIR + '/' + dest_dir)
		return dest_dir, str(uuid.uuid4()).replace('-', '')

	def CheckFreeSpace(self, request):

		fs_limit = self.GetFilesSpaceLimit(request)
		fs_size = self.GetUsedFilesSpace(request)

		if fs_size is not None and fs_limit is not None and fs_size >= fs_limit:
			raise InputException('file', 'Zbyt mało wolnej przestrzeni')

	def StoreFile(self, request, data, ext, orgFileName, mimetype, image=None):

		self.CheckFreeSpace(request)

		ext = '.' + ext.lstrip('.').lower()

		dest_dir, uniqname = self.GetNewFileName(request, orgFileName, ext)
		org_filename = "%s/%s/%s" % (self.UPLOAD_DIR, dest_dir, uniqname + ext)
		self.uniqname = uniqname

		with open(org_filename, "wb") as file:
			file.write(data)

		self.LogUpload(request, '%s/%s%s' % (dest_dir, uniqname, ext))

		return '%s/%s%s' % (dest_dir, uniqname, ext)

	def LogUpload(self, request, path):
		pass

	def DelayedCleaning(self, file):
		pass
