# -*- coding: utf-8 -*-

import os, sys
from PIL import Image, ImageEnhance
from io import StringIO

import datetime
import logging
import traceback

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

# -------------------------------------------------------------------

def OpenAndShrink(source, params, watermark=None):

	if source.format == 'GIF':

		frames = []

		w, h = source.size

		im = source
		palette = im.getpalette()
		last_frame = im.convert('RGBA')

		all_frames = []
		try:
			im.seek(0)
			for i in range(100000):

				new_frame = Image.new('RGBA', im.size)

				if im.tile:
					tag, (x0, y0, x1, y1), offset, extra = im.tile[0]

					if x1 != w or y1 != h:
						new_frame.paste(last_frame, (0, 0))

				if not im.getpalette():
					im.putpalette(palette)

				new_frame.paste(im, (0, 0), im.convert('RGBA'))

				new_frame = Transform(new_frame, params)
				last_frame = new_frame

				if params.get('watermark') and watermark:
					new_frame = PasteWatermark(new_frame, watermark)

				all_frames.append(new_frame)

				im.seek(im.tell() + 1)

		except EOFError:
			pass

		return all_frames

	if source.mode == 'RGBA':
		# białe tło dla obrazków
		if params.get('format') == 'JPEG':
			source.load()  # needed for split()
			bg = Image.new('RGB', source.size, (255, 255, 255))
			bg.paste(source, mask=source.split()[3])  # 3 is the alpha channel
			source = bg
	elif source.mode != 'RGB':
		source = source.convert('RGBA')

	source = Transform(source, params)
	if params.get('watermark') and watermark:
		source = PasteWatermark(source, watermark)

	return source

# -------------------------------------------------------------------

def Transform(img, params):

	img_w, img_h = img.size

	if not img_w or not img_h:
		return img

	thumb_type = params.get('thumb_type', 'FitWidth')

	thumb_w = params.get('width', None)
	thumb_h = params.get('height', None)

	if thumb_type == 'FitWidth' and thumb_w:
		if not thumb_h:
			if img_w > thumb_w:
				img = img.resize((thumb_w, img_h*thumb_w/img_w), Image.ANTIALIAS)
		else:
			if img_w > thumb_w or img_h > thumb_h:
				scale = max(float(img_w)/thumb_w, float(img_h)/thumb_h)
				img = img.resize((int(img_w/scale), int(img_h/scale)), Image.ANTIALIAS)

	elif thumb_type == 'FitAll' and thumb_w and thumb_h:
		if img_w > thumb_w or img_h > thumb_h:

			if float(img_w)/img_h <= float(thumb_w)/thumb_h:
				img = img.resize((thumb_w, img_h*thumb_w/img_w), Image.ANTIALIAS)
				img_w, img_h = img.size
				img = img.crop(((img_w-thumb_w)/4, (img_h-thumb_h)/2,
								(img_w-thumb_w)/4+thumb_w, (img_h-thumb_h)/2+thumb_h))
			else:
				img = img.resize((img_w*thumb_h/img_h, thumb_h), Image.ANTIALIAS)
				img_w, img_h = img.size
				img = img.crop(((img_w-thumb_w)/2, (img_h-thumb_h)/4, 
								(img_w-thumb_w)/2+thumb_w, (img_h-thumb_h)/4+thumb_h))

	elif thumb_type == 'MaxBox' and thumb_w and thumb_h:
		if img_w > thumb_w or img_h > thumb_h:
			scale = max(float(img_w)/thumb_w, float(img_h)/thumb_h)
			img = img.resize((int(img_w/scale), int(img_h/scale)), Image.ANTIALIAS)

	elif thumb_type == 'Force' and thumb_w and thumb_h:
		if img_w > thumb_w or img_h > thumb_h:
			img = img.resize((thumb_w, thumb_h), Image.ANTIALIAS)
	elif thumb_type == 'Manual' and thumb_w and thumb_h:
		img = img.resize((thumb_w, thumb_h), Image.ANTIALIAS)
		if 'crop_info' in params:
			c=params['crop_info']
			if c['width'] > 0 and c['height'] > 0:
				img_w, img_h = img.size
				img = img.crop((max(c['left'], 0), max(c['top'], 0), min(c['left']+c['width'], img_w), min(c['top']+c['height'], img_h)))

#	if 'rotate' in params:
#		img = img.rotate( params['rotate'] )

	pil_img = img

	if 'color' in params:
		pil_img = ImageEnhance.Color(pil_img).enhance( 1 + float(params['color']) / 100 )
	if 'contrast' in params:
		pil_img = ImageEnhance.Contrast(pil_img).enhance( 1 + float(params['contrast']) / 100 )
	if 'brightness' in params:
		pil_img = ImageEnhance.Brightness(pil_img).enhance( 1 + float(params['brightness']) / 100 )

	return pil_img

# ------------------------------------------------------------------------

def PasteWatermark(im, mark):

	if im.mode != 'RGBA':
		im = im.convert('RGBA')
	# create a transparent layer the size of the image and draw the
	# watermark in that layer.
	layer = Image.new('RGBA', im.size, (0,0,0,0))

	if isinstance(mark, tuple):

		frame, center = mark

		frame = frame.resize( (int(im.size[0]*.9), int(im.size[1]*.9)), Image.ANTIALIAS)
		w, h = frame.size
		layer.paste(frame, ((im.size[0] - w) / 2, (im.size[1] - h) / 2) )
		im = Image.composite(layer, im, layer)

		layer = Image.new('RGBA', im.size, (0,0,0,0))

		mark = center
		ratio = min(float(im.size[0]*0.9) / mark.size[0], float(im.size[1]*0.9) / mark.size[1])
		ratio = min( ratio, 1.0 )
	else:
		ratio = min(float(im.size[0]*.9) / mark.size[0], float(im.size[1]*.9) / mark.size[1])

	w = int(mark.size[0] * ratio)
	h = int(mark.size[1] * ratio)
	if ratio != 1.0:
		mark = mark.resize((w, h), Image.ANTIALIAS)
	layer.paste(mark, ((im.size[0] - w) / 2, (im.size[1] - h) / 2))
	# composite the watermark with the layer

	return Image.composite(layer, im, layer)

# ------------------------------------------------------------------------

def CreateThumb(image_path, thumb_path, params={}, watermark=None):

	try:
		source = Image.open(image_path)
		fmt = params.get('format') or source.format

		frames = OpenAndShrink(source, params, watermark=watermark)

		is_buf = hasattr(thumb_path, 'write')

		first_frame = frames
		if isinstance(frames, list):
			first_frame = frames[0]

		if fmt != 'GIF':
			frames = first_frame

		try:
			if fmt == 'GIF':
				if isinstance(frames, list) and len(frames) > 1:
					info = source.info
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
					save_params = dict(optimize=params.get('optimize', True), save_all=True, append_images=frames[1:], loop=info.get('loop', 0), duration=info.get('duration', 50))
				else:
					save_params = dict(optimize=params.get('optimize', True))
			elif fmt == 'JPEG':
				save_params = dict(progressive=params.get('progressive', True), quality=params.get('quality', 95), optimize=params.get('optimize', True))
			elif fmt == 'PNG':
				save_params = dict(progressive=params.get('progressive', True), quality=params.get('quality', 95), optimize=params.get('optimize', True))
			else:
				save_params = {}

			tmp = None
			if params.get('metadata') is True and not is_buf and fmt == 'JPEG':
				from iptcinfo import IPTCInfo
				info = IPTCInfo(image_path)
				if len(info.data) >= 4:
					tmp = StringIO()
					first_frame.save(tmp, fmt, **save_params)
					tmp.seek(0)

					thumb = IPTCInfo(tmp, force=True)
					for k,v in info.data.items():
						thumb.data[k] = v

					thumb.saveAs(thumb_path + '.tmp')

			if tmp is None:
				if is_buf:
					first_frame.save(thumb_path, fmt, **save_params)
				else:
					first_frame.save(thumb_path + '.tmp', fmt, **save_params)

			if not is_buf:
				os.rename(thumb_path + '.tmp', thumb_path)

		except IOError as e:
			log.error("[1] Nie można stworzyć podglądu dla pliku '%s':%s\n%s"%(image_path, e, str('\n'.join(traceback.format_exception(*sys.exc_info())),'UTF8')))

			first_frame.save(thumb_path, fmt, progressive=True, quality=95)

		if not is_buf:
			os.chmod(thumb_path, 0o644)
			for f in CreateThumb.OnNewImage:
				f(thumb_path, image_path, fmt, params)
		return thumb_path

	except Exception as e:
		log.error("[2] Nie można stworzyć podglądu dla pliku '%s':%s\n%s"%(image_path, e, str('\n'.join(traceback.format_exception(*sys.exc_info())),'UTF8')))

	return None

# Events used for images opitmisations: pngquant, gifsicle, jpegoptim
CreateThumb.OnNewImage = []

# ------------------------------------------------------------------------

handle_thumb_new = CreateThumb

def TransformAvatar(image_path, thumb_path, cx, cy):
	return CreateThumb(image_path, thumb_path, dict(thumb_type='MaxBox', width=cx, height=cy))

transform_image = Transform

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
