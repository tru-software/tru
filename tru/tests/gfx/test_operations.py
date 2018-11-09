from tru.gfx.thumbs import Operations
from PIL import Image, ImageChops
import pytest
from random import randint

def cmp_image(a, b, tolerance_perc = 2):
	assert abs(a.size[0] - b.size[0]) <= 1, "diffrent width"
	assert abs(a.size[1] - b.size[1]) <= 1, "diffrent height"

	a = a.resize((20,20), Image.ANTIALIAS)
	b = b.resize((20,20), Image.ANTIALIAS)

	a.save("tests/gfx/tmp/a.png")
	b.save("tests/gfx/tmp/b.png")

	d = ImageChops.difference(a.convert("RGBa"), b.convert("RGBa"))

	d_bytes = d.tobytes()
	msep = sum(pow((x/255)*100, 2) for x in d_bytes) / len(d_bytes)
	assert msep <= tolerance_perc

	#for y in range(20):
	#	for x in range(20):
	#		xy = x,y
	#		pix = d.getpixel(xy)
	#		assert max(pix) <= 2.56 * tolerance_perc, "color difference at position {}: {} (colors {} {})".format(xy, pix, a.getpixel(xy), b.getpixel(xy))

	return True


def test_FitWidth_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux FitWidth 200 0.png")
	res = Operations.FitWidth(200, 0)(img)
	res.save("tests/gfx/tmp/linux FitWidth 200 0.png")
	assert cmp_image(res, pat)

def test_FitAll_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux FitAll 160 160.png")
	res = Operations.FitAll(160, 160)(img)
	res.save("tests/gfx/tmp/linux FitAll 160 160.png")
	assert cmp_image(res, pat)

def test_MaxBox_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux MaxBox 160 160.png")
	res = Operations.MaxBox(160, 160)(img)
	res.save("tests/gfx/tmp/linux MaxBox 160 160.png")
	assert cmp_image(res, pat)

def test_Force_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux Force 160 160.png")
	res = Operations.Force(160, 160)(img)
	res.save("tests/gfx/tmp/linux Force 160 160.png")
	assert cmp_image(res, pat)

def test_Manual_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux Manual 160 192 18 18 131 59.png")
	res = Operations.Manual(160, 192, (18,18,131,59))(img)
	res.save("tests/gfx/tmp/linux Manual 160 192 18 18 131 59.png")
	assert cmp_image(res, pat)

def test_Contrast_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux Contrast 150.png")
	res = Operations.Contrast(150)(img)
	res.save("tests/gfx/tmp/linux Contrast 150.png")
	assert cmp_image(res, pat)

def test_Brightness_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux Brightness 150.png")
	res = Operations.Brightness(150)(img)
	res.save("tests/gfx/tmp/linux Brightness 150.png")
	assert cmp_image(res, pat)

def test_Watermark_img():
	img = Image.open("tests/gfx/op/linux.png")
	watermark = Image.open("tests/gfx/op/watermark.png")
	res = Operations.Watermark(watermark)(img)

	res.save("tests/gfx/tmp/linux Watermark watermark.png")
	pat = Image.open("tests/gfx/op/linux Watermark watermark.png")
	assert cmp_image(res, pat)



def test_FitWidth_dim():
	img1 = Image.new('RGBA', (40,4), color=(0,0,0,0))
	img2 = Image.new('RGBA', (10,15), color=(0,0,0,0))

	def test_operation(img, w, h):
		try:
			op = Operations.FitWidth(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)
			assert((w is None       and res.size[0] == img.size[0])
				or (w == 0          and res.size[0] == img.size[0])
				or (w > img.size[0] and res.size[0] == img.size[0])
				or (True            and res.size[0] == w          ))
		except:
			print("Operation failed on {} -> {}".format(img.size, (w,h)))
			raise

	for img in [img1, img2]:
		ws = [None] + list(range(0, 2 * img.size[0]))
		hs = [None] + list(range(0, 2 * img.size[1]))
		for w in ws:
			for h in hs:
				test_operation(img, w, h)


def test_FitAll_dim():
	img1 = Image.new('RGBA', (40,4), color=(0,0,0,0))
	img2 = Image.new('RGBA', (10,15), color=(0,0,0,0))

	def test_operation(img, w, h):
		try:
			op = Operations.FitAll(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)
			assert(
				((w is None or h is None) and res.size == img.size)
				or (res.size[0] <= w and res.size[1] <= h)
			)
		except:
			print("Operation failed on {} -> {}".format(img.size, (w,h)))
			raise

	for img in [img1, img2]:
		ws = [None] + list(range(0, 2 * img.size[0]))
		hs = [None] + list(range(0, 2 * img.size[1]))
		for w in ws:
			for h in hs:
				test_operation(img, w, h)


def test_MaxBox_dim():
	img1 = Image.new('RGBA', (40,4), color=(0,0,0,0))
	img2 = Image.new('RGBA', (10,15), color=(0,0,0,0))

	def test_operation(img, w, h):
		try:
			op = Operations.MaxBox(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)
			assert(
				((w is None or h is None) and res.size == img.size)
				or (res.size[0] <= w and res.size[1] <= h)
			)
		except:
			print("Operation failed on {} -> {}".format(img.size, (w,h)))
			raise

	for img in [img1, img2]:
		ws = [None] + list(range(0, 2 * img.size[0]))
		hs = [None] + list(range(0, 2 * img.size[1]))
		for w in ws:
			for h in hs:
				test_operation(img, w, h)


def test_Force_dim():
	img1 = Image.new('RGBA', (40,4), color=(0,0,0,0))
	img2 = Image.new('RGBA', (10,15), color=(0,0,0,0))

	def test_operation(img, w, h):
		try:
			op = Operations.Force(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)
			assert(
				((w is None or h is None) and res.size == img.size)
				or (res.size[0] == w and res.size[1] == h)
			)
		except:
			print("Operation failed on {} -> {}".format(img.size, (w,h)))
			raise

	for img in [img1, img2]:
		ws = [None] + list(range(0, 2 * img.size[0]))
		hs = [None] + list(range(0, 2 * img.size[1]))
		for w in ws:
			for h in hs:
				test_operation(img, w, h)


def test_Manual_dim():

	img_w,img_h = randint(1,20),randint(1,20)

	img1 = Image.new('RGBA', (img_w,img_h), color=(0,0,0,0))

	def test_operation(img, w, h, crop):
		try:

			op = Operations.Manual(w,h,crop)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)

			if crop is not None:
				cx, cy, cw, ch = crop
				assert res.size[0] <= cw and res.size[1] <= ch
			else:
				if w is not None and h is not None:
					assert res.size[0] <= w and res.size[1] <= h
				else:
					assert res.size == img.size

		except:
			print("Operation failed on {} -> {} {}".format(img.size, (w,h), crop))
			raise

	for img in [img1]:

		for i in range(10000):
			w,h = randint(0,img_w*2),randint(0,img_h*2)
			crop = randint(-img_w*3,img_h*3),randint(-img_w*3,img_h*3),randint(-img_w*4,img_h*4),randint(-img_w*4,img_h*4)

			if randint(0,20) == 0:
				w = None
			if randint(0,20) == 0:
				h = None
			if randint(0,10) == 0:
				crop = None

			test_operation(img, w, h, crop)

"""
TODO:
	Manual
	Operations.Contrast(val)
	Operations.Brightness(val)
	Operations.Watermark(center,frame)
	Operations.RotateImage    # apply exif rotation
"""
