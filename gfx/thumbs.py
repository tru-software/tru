# -*- coding: utf-8 -*-

import os, sys
from PIL import Image, ImageEnhance
from io import BytesIO

import datetime
import logging
import functools

from tru.utils.backtrace import GetTraceback
from tru.fs.utils import TmpFile

import mimetypes
mimetypes.init()

try:
	import iptcinfo3
except ImportError:
	iptcinfo3 = None

log = logging.getLogger(__name__)

# -------------------------------------------------------------------
# http://mail.python.org/pipermail/image-sig/1999-August/000816.html
# after some digging, this seems to be a limitation in
# the JPEG library (incremental decoding doesn't work
# with optimize).
# 
# you might be able to work around this by making
# PIL's output buffer large enough to hold the entire
# output image:
# 
# import ImageFile
# ImageFile.MAXBLOCK = 1000000 # default is 64k
# 
# im.save("file.jpg", optimize=1)

from PIL import ImageFile
ImageFile.MAXBLOCK = 4096 * 3 * 1024 * 4 # default is 64k

# -------------------------------------------------------------------

from PIL import Image, ImageEnhance, ImageFile
from PIL.GifImagePlugin import GifImageFile, _accept, _save, _save_all

"""
class BetterGifImageFile(GifImageFile):

    def load_end(self):
        ImageFile.ImageFile.load_end(self)
        self._prev_im = self.im.copy()

Image.register_open(BetterGifImageFile.format, BetterGifImageFile, _accept)
Image.register_save(BetterGifImageFile.format, _save)
Image.register_save_all(BetterGifImageFile.format, _save_all)
Image.register_extension(BetterGifImageFile.format, ".gif")
Image.register_mime(BetterGifImageFile.format, "image/gif")
"""

class ThumbError(Exception):
	pass


def coalesce(*args):
	for i in args:
		if i is not None:
			return i

# -------------------------------------------------------------------

try:
	range = xrange
except NameError:
	pass

# -------------------------------------------------------------------

def Transform(source, ops):

	if source.format == 'GIF':

		frames = []

		w, h = source.size

		im = source
		palette = im.getpalette()
		last_frame = im.convert('RGBA')

		all_frames = []
		try:
			im.seek(0)
			ops = list(ops)
			for i in range(100000):

				new_frame = Image.new('RGBA', im.size)

				if im.tile:
					tag, (x0, y0, x1, y1), offset, extra = im.tile[0]

					if x1 != w or y1 != h:
						new_frame.paste(last_frame, (0, 0))

				if not im.getpalette():
					im.putpalette(palette)

				new_frame.paste(im, (0, 0), im.convert('RGBA'))

				for op in ops:
					new_frame = op(new_frame)

				last_frame = new_frame

				all_frames.append(new_frame)

				im.seek(im.tell() + 1)

		except EOFError:
			pass

		return all_frames

	"""
	if source.mode == 'RGBA':
		# białe tło dla obrazków
		if params.get('format') == 'JPEG':
			source.load()  # needed for split()
			bg = Image.new('RGB', source.size, (255, 255, 255))
			bg.paste(source, mask=source.split()[3])  # 3 is the alpha channel
			source = bg
	"""
	if source.mode != 'RGB':
		source = source.convert('RGBA')

	for op in ops:
		source = op(source)

	return source

# -------------------------------------------------------------------

class Operations(object):

	class Base(object):
		pass

	class Transform(Base):

		def __call__(self, im):
			return self.Exec(im)

	class TransformSize(Transform):

		def __init__(self, width, height):
			self.w = width
			self.h = height

		def GetFinalSize(self, w, h):
			return (w, h)

	class RotateImage(Transform):

		def __init__(self):
			pass

		exif_orientation_tag = 0x0112 # contains an integer, 1 through 8
		exif_transpose_sequences = [  # corresponding to the following
			[],
			[Image.FLIP_LEFT_RIGHT],
			[Image.ROTATE_180],
			[Image.FLIP_TOP_BOTTOM],
			[Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],
			[Image.ROTATE_270],
			[Image.FLIP_TOP_BOTTOM, Image.ROTATE_90],
			[Image.ROTATE_90],
		]

		def Exec(self, im):
			try:
				self.seq = self.exif_transpose_sequences[im._getexif()[self.exif_orientation_tag] - 1]
			except Exception:
				return im
			return functools.reduce(lambda im, op: im.transpose(op), seq, im)


	class FitWidth(TransformSize):

		def Exec(self, img):

			if not self.w:
				return img

			img_w, img_h = img.size

			if not self.h:
				if img_w > self.w:
					img = img.resize((thumb_wself.wimg_h*self.w/img_w), Image.ANTIALIAS)
			else:
				if img_w > self.w or img_h > self.h:
					scale = max(float(img_w)/self.w, float(img_h)/self.h)
					img = img.resize((int(img_w/scale), int(img_h/scale)), Image.ANTIALIAS)

			return img

		def GetFinalSize(self, img_w, img_h):

			if not self.w:
				return (img_w, img_h)

			if not self.h:
				if img_w > self.w:
					return (self.w, img_h*self.w/img_w)
			else:
				if img_w > self.w or img_h > self.h:
					scale = max(float(img_w)/self.w, float(img_h)/self.h)
					return (img_w//scale, img_h//scale)

			return (img_w, img_h)


	class FitAll(TransformSize):

		def Exec(self, img):

			if not self.w or not self.h:
				return img

			img_w, img_h = img.size

			if img_w > self.w or img_h > self.h:

				if float(img_w)/img_h <= float(self.w)/self.h:
					img = img.resize((self.w, img_h*self.w//img_w), Image.ANTIALIAS)
					img_w, img_h = img.size
					img = img.crop(((img_w-self.w)/4, (img_h-self.h)/2, (img_w-self.w)/4+self.w, (img_h-self.h)/2+self.h))
				else:
					img = img.resize((img_w*self.h//img_h, self.h), Image.ANTIALIAS)
					img_w, img_h = img.size
					img = img.crop(((img_w-self.w)/2, (img_h-self.h)/4, (img_w-self.w)/2+self.w, (img_h-self.h)/4+self.h))

			return img

		def GetFinalSize(self, img_w, img_h):
			return (min(self.w, img_w), min(self.h, img_h))


	class MaxBox(TransformSize):

		def Exec(self, img):

			if not self.w or not self.h:
				return img

			img_w, img_h = img.size

			if img_w > self.w or img_h > self.h:
				scale = max(float(img_w)/self.w, float(img_h)/self.h)
				img = img.resize((int(img_w//scale), int(img_h//scale)), Image.ANTIALIAS)

			return img

		def GetFinalSize(self, img_w, img_h):
			scale = max(float(img_w)/self.w, float(img_h)/self.h)
			return (img_w//scale, img_h//scale)


	class Force(TransformSize):

		def Exec(self, img):

			if not self.w or not self.h:
				return img

			img_w, img_h = img.size

			if img_w > thumb_w or img_h > thumb_h:
				img = img.resize((thumb_w, thumb_h), Image.ANTIALIAS)

			return img

		def GetFinalSize(self, img_w, img_h):
			return (min(self.w, img_w), min(self.h, img_h))


	class Manual(TransformSize):

		def __init__(self, width, height, crop):
			self.w = width
			self.h = height
			self.c = crop  # (left, top, width, height)
			if crop == (0,0,0,0):
				self.c = None

		def Exec(self, img):

			if not self.w or not self.h:
				return img

			img = img.resize((self.w, self.h), Image.ANTIALIAS)
			if self.c:
				left, top, width, height = self.c
				if width > 0 and height > 0:
					img_w, img_h = img.size
					img = img.crop((max(left, 0), max(top, 0), min(left+width, img_w), min(top+height, img_h)))

			return img

		def GetFinalSize(self, img_w, img_h):
			if self.c:
				left, top, width, height = self.c
				return (width, height)
			return (self.w, self.h)

	class Color(Transform):

		def __init__(self, value):
			self.v = 1+float(value)/100

		def Exec(self, img):
			return ImageEnhance.Color(img).enhance(self.v)

	class Contrast(Color):
		def Exec(self, img):
			return ImageEnhance.Contrast(img).enhance(self.v)

	class Brightness(Color):
		def Exec(self, img):
			return ImageEnhance.Brightness(img).enhance(self.v)


	class Watermark(Transform):

		def __init__(self, center, frame=None):
			self.center = center
			self.frame = frame

		def Exec(self, im):

			mark = self.center

			if im.mode != 'RGBA':
				im = im.convert('RGBA')
			# create a transparent layer the size of the image and draw the
			# watermark in that layer.
			layer = Image.new('RGBA', im.size, (0, 0, 0, 0))

			# TODO: cache resized watermarks

			if self.frame:

				frame = self.frame

				frame = frame.resize( (int(im.size[0]*.9), int(im.size[1]*.9)), Image.ANTIALIAS)
				w, h = frame.size
				layer.paste(frame, ((im.size[0] - w) // 2, (im.size[1] - h) // 2))
				im = Image.composite(layer, im, layer)

				layer = Image.new('RGBA', im.size, (0, 0, 0, 0))

				ratio = min(float(im.size[0]*0.9) / mark.size[0], float(im.size[1]*0.9) / mark.size[1])
				ratio = min(ratio, 1.0)
			else:
				ratio = min(float(im.size[0]*.9) / mark.size[0], float(im.size[1]*.9) / mark.size[1])

			w = int(mark.size[0] * ratio)
			h = int(mark.size[1] * ratio)
			if ratio != 1.0:
				mark = mark.resize((w, h), Image.ANTIALIAS)
			layer.paste(mark, ((im.size[0] - w) // 2, (im.size[1] - h) // 2))

			return Image.composite(layer, im, layer)


	class SaveToBuf(Base):

		def __init__(self, format=None, quality=None, optimize=None, progressive=None, metadata=None, bgcolor=None):
			self.format = format
			self.optimize = optimize if optimize is not None else True
			self.progressive = progressive if progressive is not None else True
			self.quality = quality if quality is not None else 95
			self.metadata = metadata if metadata is not None else False
			self.bgcolor = bgcolor or (255, 255, 255)

			#if iptcinfo3 is None and self.metadata:
				#raise ImportError("Cannot import iptcinfo3 module")

		def Clone(self, format=None, quality=None, optimize=None, progressive=None, metadata=None, bgcolor=None):
			return Operations.SaveToBuf(
				format=coalesce(format, self.format),
				quality=coalesce(quality, self.quality),
				optimize=coalesce(optimize, self.optimize),
				progressive=coalesce(progressive, self.progressive),
				metadata=coalesce(metadata, self.metadata),
				bgcolor=coalesce(bgcolor, self.bgcolor)
			)

		def __call__(self, src_path, src, buf, frames):

			first_frame = frames[0] if isinstance(frames, list) else frames
			fmt = self.format or src.format

			if fmt != 'GIF': # or PNG - TODO
				frames = first_frame

			if fmt == 'GIF':
				if isinstance(frames, list) and len(frames) > 1:
					info = src.info
					"""
					{
						'background': 0,
						'duration': 50,
						'extension': ('XMP DataXMP', 814),
						'loop': 0,
						'transparency': 255,
						'version': 'GIF89a'
					}
					"""
					save_params = dict(optimize=self.optimize, save_all=True, append_images=frames[1:], loop=info.get('loop', 0), duration=info.get('duration', 50))
				else:
					save_params = dict(optimize=self.optimize)
			elif fmt == 'JPEG':

				if first_frame.mode == 'RGBA':
					background = Image.new('RGBA', first_frame.size, self.bgcolor)
					first_frame = Image.alpha_composite(background, first_frame)
					first_frame = first_frame.convert('RGB')

				save_params = dict(progressive=self.progressive, quality=self.quality, optimize=self.optimize)

			elif fmt == 'PNG':
				save_params = dict(progressive=self.progressive, quality=self.quality, optimize=self.optimize)
			else:
				save_params = {}


			if self.metadata is True and fmt == 'JPEG' and src.format == 'JPEG':

				if iptcinfo3 is None:
					raise ImportError("Cannot import iptcinfo3 module")

				info = iptcinfo3.IPTCInfo(src_path)
				if len(info.data) >= 4:

					buf_tmp = BytesIO()
					first_frame.save(buf_tmp, fmt, **save_params)
					buf_tmp.seek(0)

					try:
						thumb = iptcinfo3.IPTCInfo(buf_tmp, force=True)
						for k, v in info.data.items():
							thumb.data[k] = v
						thumb.saveToBuf(buf)
						return
					except Exception as ex:
						log.error("Cannot set iptc data to JPEG file: %s", ex, exc_info=ex)


			first_frame.save(buf, fmt, **save_params)


# ------------------------------------------------------------------------

def CreateThumb(image_path, thumb_path, operations, save):

	try:
		source = Image.open(image_path)
		frames = Transform(source, operations)

		if hasattr(thumb_path, 'write'):
			fmt = save(image_path, source, thumb_path, frames)
			return thumb_path

		with TmpFile(thumb_path, mode="wb", perms=0o644) as f:
			fmt = save(image_path, source, f, frames)

		for f in CreateThumb.OnNewImage:
			f(thumb_path, image_path, fmt, {})

		return thumb_path

	except IOError as e:
		log.error("Cannot store thumbnail '%s':%s\n%s"%(image_path, e, GetTraceback(e)))
		raise ThumbError("Cannot store thumbnail: {}".format(e))

	except Exception as e:
		log.error("Cannot create thumbnail '%s':%s\n%s"%(image_path, e, GetTraceback(e)))
		raise ThumbError("Cannot create thumbnail: {}".format(e))

# Callbacks used for new images opitmisations: pngquant, gifsicle, jpegoptim; see ImageExternalOpt
CreateThumb.OnNewImage = []

# ------------------------------------------------------------------------

def ImageExternalOpt(image_path):

	if not os.path.isfile(image_path):
		raise ValueError('Not such file: "{}"'.format(image_path))

	mimetype, encoding = mimetypes.guess_type(image_path)
	mimetype = mimetype or 'unknown'

	if not mimetype.startswith('image/'):
		raise ValueError('File is not an image: "{}"'.format(image_path))

	output = image_path + '.tmp'
	if os.path.isfile(output):
		os.remove(output)

	org_size = os.path.getsize(image_path)

	if mimetype == 'image/png':
		process = subprocess.Popen(['pngquant', '--quality', '60-80', '--speed', '3', '--output', output, image_path], stdout=subprocess.PIPE)
	elif mimetype == 'image/jpeg':
		shutil.copyfile(image_path, output)
		process = subprocess.Popen(['jpegoptim', '-qso', '-m90', output], stdout=subprocess.PIPE)
	elif mimetype == 'image/gif':
		process = subprocess.Popen(['gifsicle', '-b', '-O3', '-o', output, image_path], stdout=subprocess.PIPE)
	else:
		raise ValueError('Unsupported image type "{}": "{}"'.format(mimetype, image_path))

	# process.returncode
	process.wait()

	opt_size = os.path.getsize(output)
	if not os.path.isfile(output):
		raise ValueError('Cannot opt image ({}): "{}"'.format(process.returncode, image_path))

	if opt_size and opt_size < org_size:
		os.rename(image, image_path + '.org')
		os.rename(output, image_path)
		os.remove(image_path + '.org')
		return (org_size, opt_size)

	os.remove(output)
	return (org_size, opt_size)

# ------------------------------------------------------------------------

def GetImageSize(path):

	if not os.path.isfile( path ):
		return None

	try:
		with Image.open( path ) as im:
			return im.size
	except IOError:
		pass

	return None

# ------------------------------------------------------------------------
