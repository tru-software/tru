# -*- coding: utf-8 -*-

try:
	# Py2:
	import urllib2
	from urllib import quote

	str_or_unicode = unicode

	PY2 = True

except ImportError:
	# Py3:
	import urllib.request, urllib.error, urllib.parse
	from urllib.parse import quote

	basestring = str
	str_or_unicode = str

	PY2 = False

import re
import os, os.path
import copy
import zlib
import collections
from struct import pack, unpack
from base64 import urlsafe_b64decode, urlsafe_b64encode

from tru.fs.utils import path_replace_ext
from tru.io.hash import Hash, Distribution, EncodeHash, DecodeHash
from .thumbs import Operations


class ImageType(object):

	# ---------------------------------------------------------------------------------------

	class ThumbSize(object):

		op_code = None  # Overwrite!

		def get_params(self, d):
			pass

		def calcCropSizeFrom(self, w, h, best_case=False):
			return (w, h)

		def type_name(self):
			d={}
			self.get_params(d)
			return d['thumb_type']

		def get_size(self):
			return (None, None)

		def _getOpParams(self):
			return pack('!HH', self.w or 0, self.h or 0)

		def GetCropWithPoint(self, img_w, img_h, x, y):
			return None

		@classmethod
		def decode(cls, data):
			return cls(*unpack('!HH', data[:4]))

		@classmethod
		def FromParams(cls, params):
			return cls()

		def GetNoPictureSizeInts(self):
			return (77, 77)


	class Original(ThumbSize):

		op_code = 0x01

		def __init__(self):
			pass

		def get_params(self, d):
			d['thumb_type'] = 'Org'

		def __unicode__(self):
			return 'Bez zmian'

		def get_size(self):
			return (None, None)

		@classmethod
		def decode(cls, data):
			return cls()

		def _getOpParams(self):
			return pack('!B', 0x44)


	class FitWidth(ThumbSize, Operations.FitWidth):

		op_code = 0x02

		def __init__(self, cx, cy=None, expand=False):
			super(ImageType.FitWidth, self).__init__(cx, cy)
			self.expand = expand

		def get_params(self, d):
			d['thumb_type'] = 'FitWidth'
			d['width'] = self.w
			if self.h:
				d['height'] = self.h

		def calcCropSizeFrom(self, w, h, best_case=False):
			return self.GetFinalSize(w, h)

		def get_size(self):
			return (self.cx, self.cy)

		@classmethod
		def FromParams(cls, params):
			return cls(params['width'])

		def __unicode__(self):
			if self.cy:
				return 'Do wielkości max: %sx%s' % (self.w, self.h)
			return 'Do szerokości: %s' % (self.w)

		def GetNoPictureSizeInts(self):
			return self.w, self.h


	class FitAll(ThumbSize, Operations.FitAll):

		op_code = 0x03

		def __init__(self, cx, cy):
			super(ImageType.FitAll, self).__init__(cx, cy)

		def get_params(self, d):
			d['thumb_type'] = 'FitAll'
			d['width'] = self.w
			d['height'] = self.h

		def _getOpParams(self):
			return pack('!HH', self.w, self.h)

		def calcCropSizeFrom(self, w, h, best_case=False):
			return self.GetFinalSize(w, h)

		def get_size(self):
			return (self.w, self.h)

		def GetCropWithPoint(self, img_w, img_h, x, y):

			thumb_w, thumb_h = self.w, self.h

			if img_w <= thumb_w and img_h <= thumb_h:
				return None

			if float(img_w)/img_h <= float(thumb_w)/thumb_h:
				ratio = float(thumb_w)/img_w
				w, h = thumb_w, int(img_h*ratio)
				x, y = int(x * ratio), int(y * ratio)

				half_h = (thumb_h/2)
				if y < half_h:
					y = half_h
				elif y > (h - half_h):
					y = (h - half_h)

				crop = (0, y-half_h, thumb_w, thumb_h)

			else:
				ratio = float(thumb_h)/img_h
				w, h = int(img_w*ratio), thumb_h
				x, y = int(x * ratio), int(y * ratio)

				half_w = (thumb_w/2)
				if x < half_w:
					x = half_w
				elif x > (w - half_w):
					x = (w - half_w)

				crop = (x-half_w, 0, thumb_w, thumb_h)

			return ImageType.Manual(w, h, crop)

		def __unicode__(self):
			return 'Wyrównanie do: %sx%s' % (self.w, self.h)

		@classmethod
		def FromParams(cls, params):
			return cls(params['width'], params['height'])

		def GetNoPictureSizeInts(self):
			return self.w, self.h


	class Force(ThumbSize, Operations.Force):

		op_code = 0x04

		def __init__(self, cx, cy):
			super(ImageType.Force, self).__init__(cx, cy)

		def get_params(self, d):
			d['thumb_type'] = 'Force'
			d['width'] = self.w
			d['height'] = self.h

		def calcCropSizeFrom(self, w, h, best_case=False):
			return self.GetFinalSize(w, h)

		def get_size(self):
			return (self.w, self.h)

		def __unicode__(self):
			return 'Dokładnie: %sx%s' % (self.w, self.h)

		@classmethod
		def FromParams(cls, params):
			return cls(params['width'], params['height'])

		def GetNoPictureSizeInts(self):
			return self.w, self.h


	class MaxBox(ThumbSize, Operations.MaxBox):

		op_code = 0x05

		def __init__(self, cx, cy):
			super(ImageType.MaxBox, self).__init__(cx, cy)

		def get_params(self, d):
			d['thumb_type'] = 'MaxBox'
			d['width'] = self.w
			d['height'] = self.h

		def calcCropSizeFrom(self, w, h, best_case=False):
			return self.GetFinalSize(w, h)

		def get_size(self):
			return (self.w, self.h)

		def __unicode__(self):
			return 'Całość do max: %sx%s' % (self.w, self.h)

		@classmethod
		def FromParams(cls, params):
			return cls(params['width'], params['height'])

		def GetNoPictureSizeInts(self):
			return self.w, self.h


	class Manual(ThumbSize, Operations.Manual):

		op_code = 0x06

		def __init__(self, cx, cy, crop=None):
			super(ImageType.Manual, self).__init__(cx, cy, crop)

		def get_params(self, d):
			d['thumb_type'] = 'Manual'
			d['width'] = self.w
			d['height'] = self.h
			if self.c:
				d['crop_info'] = dict(left=self.c[0], top=self.c[1], width=self.c[2], height=self.c[3])

		def calcCropSizeFrom(self,w, h, best_case=False):
			raise NotImplementedError('Ciekawe kiedy to jest wywoływane')

		def get_size(self):
			if self.c:
				return (self.c[2], self.c[3])
			return (self.w, self.h)

		def _getOpParams(self):
			c = self.c or (0, 0, 0, 0)
			return pack('!HHHHHH', min(max(self.w or 0, 0), 0xFFFF), min(max(self.h or 0, 0), 0xFFFF), *c)

		@classmethod
		def decode(cls, data):
			params = unpack('!HHHHHH', data[:12])
			return cls(params[0], params[1], params[2:])

		def __unicode__(self):
			return 'Manualnie: {}x{} + crop {}'.format(self.w, self.h, self.c)

		@classmethod
		def FromParams(cls, params):
			crop = [params['crop_info'][i] for i in ('left', 'top', 'width', 'height')] if 'crop_info' in params else None

			width = params.get('width')
			height = params.get('height')

			return cls(width, height, crop)

		def GetNoPictureSizeInts(self):
			return self.get_size()

	# ---------------------------------------------------------------------------------------

	def __init__(self, id, thumb, format='JPEG', descr='', watermark=False, prefix='w', restricted=False,
				metadata=False, progressive=True, quality=95, optimize=True):
		self.id = id
		self.thumb = thumb
		self.descr = descr
		self.watermark = watermark
		self.prefix = prefix
		self.restricted = restricted
		self.color = 0
		self.contrast = 0
		self.brightness = 0
		self.deprecated = False
		self.tmp_preview = False
		self.is_custom = False
		self.save_to = Operations.SaveToBuf(format=format, progressive=progressive, quality=quality, optimize=optimize, metadata=metadata)

	def get_path(self, image_path, keep_org_ext=False, postfix=None, force_custom=False, force_format=None):

		if isinstance(self.thumb, ImageType.Original) and not force_custom:
			return image_path

		fmt = force_format or self.save_to.format

		ext = 'jpg'
		if fmt == 'GIF':
			ext = 'gif'
		elif fmt == 'PNG':
			ext = 'png'
		elif fmt == 'JPEG':
			ext = 'jpg'
		else:
			if keep_org_ext:
				ext = None

		return path_replace_ext(image_path, ext, postfix or ('_%s' % self.id))

	def get_params(self, dict=None):
		dict = dict if dict is not None else {}

		if self.thumb is not None:
			self.thumb.get_params(dict)
		if self.save_to.format is not None:
			dict['format'] = self.save_to.format
		if self.watermark:
			dict['watermark'] = True
		if self.save_to.metadata:
			dict['metadata'] = True

		dict['progressive'] = self.save_to.progressive
		dict['quality'] = self.save_to.quality
		dict['optimize'] = self.save_to.optimize
		dict['color'] = self.color
		dict['contrast'] = self.contrast
		dict['brightness'] = self.brightness
		return dict

	def GetOps(self, watermark=None, allow_resize=True):
		# Returns list of image transformations
		if allow_resize is True and isinstance(self.thumb, Operations.Transform):
			yield self.thumb
		if self.color:
			yield Operations.Color(self.color)
		if self.contrast:
			yield Operations.Contrast(self.contrast)
		if self.brightness:
			yield Operations.Brightness(self.brightness)
		if self.watermark and watermark is not None:
			yield watermark

	def PublicId(self):
		return self.prefix + str(self.id)

	classes = [
		Original, FitAll, FitWidth, Force, MaxBox, Manual
	]
	classes_map = {i.op_code:i for i in classes}
	classes_map_by_name = {i.__name__:i for i in classes}
	classes_map_by_name['Org'] = Original

	url_fmt_re = re.compile('[0-9a-zA-Z_\-=]+')

	@staticmethod
	def Decode(data, filename, key):

		assert isinstance(key, bytes), "Key must be an instance of bytes, got {}".format(repr(key))

		if not ImageType.url_fmt_re.match(data):
			raise ValueError('Invalid fmt data: {}'.format(data))

		filename = filename.encode('utf8') if isinstance(filename, str_or_unicode) else filename
		data = urlsafe_b64decode(data.encode('ascii') if isinstance(data, str_or_unicode) else data)

		format, quality, op_code, color, contrast, brightness = unpack('!BBBbbb', data[0:6])

		# Nowa wersja hash (zlib.adler32)
		trx = data[:-4]
		org_hash = unpack('!I', data[-4:])[0]
		trx_hash = Hash(key + trx + filename)

		if org_hash != trx_hash:
			# Hash może być wyliczany z dwóch różnych źródeł: oryginalna nazwa pliku lub zakodowana do url (urlencoded)
			# Sprawdzane są oba przypadki - któryś może być prawdziwy.
			trx_hash = Hash(key + trx + '/'.join(map(quote, (i.encode('utf8') for i in filename.decode('utf8').split('/')))).encode('ascii'))


		if PY2:
			# Stara wersja buildin.hash, który stał się niedeterministyczny pomiędzy instancjami python3
			# https://docs.python.org/3/reference/datamodel.html#object.__hash__
			# Note By default, the __hash__() values of str, bytes and datetime objects are “salted” with an unpredictable random value. 
			# Although they remain constant within an individual Python process, they are not predictable between repeated invocations of Python.
			# This is intended to provide protection against a denial-of-service caused by carefully-chosen inputs that exploit the worst case performance of a dict insertion, O(n^2) complexity.
			# See http://www.ocert.org/advisories/ocert-2011-003.html for details.
			# Changing hash values affects the iteration order of dicts, sets and other mappings. Python has never made guarantees about this ordering (and it typically varies between 32-bit and 64-bit builds).

			if org_hash != trx_hash:
				trx = data[:-8]
				org_hash = unpack('!q', data[-8:])[0]
				trx_hash = hash(key + trx + filename)

			if org_hash != trx_hash:
				# Hash może być wyliczany z dwóch różnych źródeł: oryginalna nazwa pliku lub zakodowana do url (urlencoded)
				# Sprawdzane są oba przypadki - któryś może być prawdziwy.
				trx_hash = hash(key + trx + '/'.join(map(quote, (i.encode('utf8') for i in filename.decode('utf8').split('/')))))

		if org_hash != trx_hash:
			raise ValueError('Invalid checksum {} != {}'.format(org_hash, trx_hash))

		progressive = False
		optimize = bool(format & 0x20)
		tmp_preview = bool(format & 0x10)
		force_format = format & 0x0F
		if force_format == 0x01:
			format = None
		elif force_format == 0x02:
			format = 'JPEG'
		elif force_format == 0x03:
			format = 'JPEG'
			progressive = True
		elif force_format == 0x04:
			format = 'PNG'
		elif force_format == 0x05:
			format = 'GIF'

		thumb = ImageType.classes_map[op_code].decode(trx[6:])
		it = ImageType(0x9999, thumb, format, 'Custom format', watermark=False, prefix='', quality=quality, progressive=progressive, optimize=optimize)

		it.color = color
		it.contrast = contrast
		it.brightness = brightness
		it.tmp_preview = tmp_preview

		return it

	def Encode(self, filename, key, **kwargs):

		assert isinstance(key, bytes), "Key must be an instance of bytes, got {}".format(repr(key))

		format = 0x01  # Default

		force_format = kwargs.get('format') or self.save_to.format or 'JPEG'
		if force_format == 'JPEG':
			format = 0x02
			if kwargs.get('progressive') is True or self.save_to.progressive is True:
				format = 0x03  # JPEG+progressive
		elif force_format == 'PNG':
			format = 0x04
		elif force_format == 'GIF':
			format = 0x05

		if self.tmp_preview:
			format &= 0x10

		if self.save_to.optimize:
			format &= 0x20

		color, contrast, brightness = self.color, self.contrast, self.brightness
		if 'color' in kwargs:
			color = kwargs['color']
		if 'contrast' in kwargs:
			contrast = kwargs['contrast']
		if 'brightness' in kwargs:
			brightness = kwargs['brightness']

		trx = pack('!BBBbbb', format, self.save_to.quality, self.thumb.op_code, color, contrast, brightness) + self.thumb._getOpParams()

		if ((len(trx)+4) % 3):
			trx += pack('!B', 0) * (3-((len(trx)+4) % 3))

		trx_hash = Hash(key + trx + filename.encode('utf8'))
		return urlsafe_b64encode(trx + pack('!I', trx_hash)).decode('ascii')

	def Clone(self, thumb=None, is_custom=None):
		c = copy.copy(self)
		if thumb is not None:
			c.thumb = thumb
		if is_custom is not None:
			c.is_custom = is_custom
		return c

	def Upgrade(self, custom_params, imsize, focuspt):

		conv = self

		if custom_params.get('thumb_type') == 'Manual':
			c = custom_params
			if 'crop_info' in c:
				crop = [c['crop_info'][i] for i in ('left', 'top', 'width', 'height')]
			else:
				crop = None
			if crop is not None:
				for i in crop:
					if i < 0 or i > 0xFFFF:
						raise ValueError("crop value {} is out of ({}, {}): {}".format(i, 0, 0xFFFF, crop))

			conv_cx, conv_cy = conv.thumb.get_size()
			width = c.get('width') or conv_cx
			height = c.get('height') or conv_cy

			conv = self.Clone(ImageType.Manual(width, height, crop), True)

		elif focuspt is not None and imsize:
			conv = conv.GetCropWithPoint(imsize[0], imsize[1], focuspt[0], focuspt[1]) or conv

		return conv

	def GetCropWithPoint(self, img_w, img_h, x, y):
		if not self.thumb:
			return None
		manual_thumb = self.thumb.GetCropWithPoint(img_w, img_h, x, y)
		if not manual_thumb:
			return None
		return self.Clone(manual_thumb, True)

	def GetNoPictureSize(self):
		return '{}x{}'.format(*self.GetNoPictureSizeInts())

	def GetNoPictureSizeInts(self):
		if not self.thumb:
			return (77, 77)
		return self.thumb.GetNoPictureSizeInts()

	def __unicode__(self):
		return 'ImageType.{}({}, {})'.format(self.thumb.__class__.__name__, self.id, self.get_params())

# -------------------------------------------------------------------------------------------

class CustomImageType(ImageType):

	def __init__(self, *args, **kwargs):
		super(CustomImageType, self).__init__(*args, **kwargs)
		self.is_custom = True

# -------------------------------------------------------------------------------------------

class TemporaryImageType(ImageType):

	def __init__(self, params={}):

		thumb_type = params.get('thumb_type')

		if thumb_type in self.classes_map_by_name:
			thumb = self.classes_map_by_name[thumb_type].FromParams(params)
		else:
			thumb = None

		super(TemporaryImageType, self).__init__(0x9996, thumb, None, 'Custom temp format', watermark=False, prefix='', quality=80)
		self.tmp_preview = True
		self.is_custom = True

		if 'color' in params:
			self.color = params['color']
		if 'contrast' in params:
			self.contrast = params['contrast']
		if 'brightness' in params:
			self.brightness = params['brightness']

		self.deprecated = True

