# -*- coding: utf-8 -*-

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
ImageFile.MAXBLOCK = 4096 * 3 * 1024 * 4  # default is 64k
ImageFile.LOAD_TRUNCATED_IMAGES = True  # https://stackoverflow.com/questions/42671252/python-pillow-valueerror-decompressed-data-too-large

# -------------------------------------------------------------------
# Fix for animated gifs with different color-palettes for each frame.

from PIL import Image, ImageFile
from PIL.GifImagePlugin import GifImageFile, _accept, _save, _save_all

class AnimatedGifImageFile(GifImageFile):

	def load_prepare(self):
		ImageFile.ImageFile.load_prepare(self)

	def load_end(self):
		ImageFile.ImageFile.load_end(self)


Image.register_open(AnimatedGifImageFile.format, AnimatedGifImageFile, _accept)
Image.register_save(AnimatedGifImageFile.format, _save)
Image.register_save_all(AnimatedGifImageFile.format, _save_all)
Image.register_extension(AnimatedGifImageFile.format, ".gif")
Image.register_mime(AnimatedGifImageFile.format, "image/gif")

# -------------------------------------------------------------------
