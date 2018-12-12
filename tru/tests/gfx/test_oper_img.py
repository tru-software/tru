import pytest
from tru.gfx.thumbs import Operations
from PIL import Image, ImageChops

tolerance = 2


def img_size_diff(a, b):
	""" Return max difference between dimensions of images 'a and 'b. """
	return max(abs(a.size[0] - b.size[0]), abs(a.size[1] - b.size[1]))

def img_visual_diff(a, b):
	""" Return visual difference between two images as number
	with 0 (no difference) and >2 (significant difference).
	"""
	assert abs(a.size[0] - b.size[0]) <= 1, "diffrent width"
	assert abs(a.size[1] - b.size[1]) <= 1, "diffrent height"

	a = a.resize((20,20), Image.ANTIALIAS)
	b = b.resize((20,20), Image.ANTIALIAS)

	a.save("tests/gfx/tmp/a.png")
	b.save("tests/gfx/tmp/b.png")

	d = ImageChops.difference(a.convert("RGBa"), b.convert("RGBa"))

	d_bytes = d.tobytes()
	mse = sum(pow((x/255)*100, 2) for x in d_bytes) / len(d_bytes)
	return mse


def test_FitWidth_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux FitWidth 200 0.png")
	res = Operations.FitWidth(200, 0)(img)
	res.save("tests/gfx/tmp/linux FitWidth 200 0.png")
	assert img_size_diff(res, pat) <= 1
	assert img_visual_diff(res, pat) <= tolerance

def test_FitAll_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux FitAll 160 160.png")
	res = Operations.FitAll(160, 160)(img)
	res.save("tests/gfx/tmp/linux FitAll 160 160.png")
	assert img_size_diff(res, pat) <= 1
	assert img_visual_diff(res, pat) <= tolerance

def test_MaxBox_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux MaxBox 160 160.png")
	res = Operations.MaxBox(160, 160)(img)
	res.save("tests/gfx/tmp/linux MaxBox 160 160.png")
	assert img_size_diff(res, pat) <= 1
	assert img_visual_diff(res, pat) <= tolerance

def test_Force_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux Force 160 160.png")
	res = Operations.Force(160, 160)(img)
	res.save("tests/gfx/tmp/linux Force 160 160.png")
	assert img_size_diff(res, pat) <= 1
	assert img_visual_diff(res, pat) <= tolerance

def test_Manual_img():
	img = Image.open("tests/gfx/op/linux.png")
	pat = Image.open("tests/gfx/op/linux Manual 160 192 18 18 131 59.png")
	res = Operations.Manual(160, 192, (18,18,131,59))(img)
	res.save("tests/gfx/tmp/linux Manual 160 192 18 18 131 59.png")
	assert img_size_diff(res, pat) <= 1
	assert img_visual_diff(res, pat) <= tolerance

def test_Watermark_img():
	img = Image.open("tests/gfx/op/linux.png")
	watermark = Image.open("tests/gfx/op/watermark.png")
	res = Operations.Watermark(watermark)(img)

	res.save("tests/gfx/tmp/linux Watermark watermark.png")
	pat = Image.open("tests/gfx/op/linux Watermark watermark.png")
	assert img_size_diff(res, pat) <= 1
	assert img_visual_diff(res, pat) <= tolerance

def test_RotateImage_img():
	# exiftool -Orientation -n img.png
	# exiftool -Orientation=8 -n img.png
	# convert img.png -auto-orient out.png


	for i in range(1,9):
		pat = Image.open("tests/gfx/op/linux {}.png".format(i))
		img = Image.open("tests/gfx/op/linux exif-orientation-{}.png".format(i))
		res = Operations.RotateImage()(img)
		res.save("tests/gfx/tmp/linux exif-orientation-{} RotateImage.png".format(i))
		assert img_size_diff(res, pat) <= 0, "RotateImage failed: different image size on exif-orientation-{}".format(i)
		assert img_visual_diff(res, pat) <= 0, "RotateImage failed: different image content on exif-orientation-{}".format(i)



