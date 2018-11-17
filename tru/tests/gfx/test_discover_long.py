from tru.gfx.thumbs import Operations
from PIL import Image, ImageChops
import pytest
from random import randint

def range2(w, h):
	for w in range(w):
		for h in range(h):
			yield (w,h)


def write_test(op_name, params, img_size, res_size):
	s = (
		"\timg = Image.new('RGBa', {img_size}, color=(0,0,0,0))\n"
		"\tassert Operations.{op_name}{params}(img).size == {res_size}\n"
	).format(
		op_name = op_name,
		params = params,
		img_size = img_size,
		res_size = res_size,
	)
	print(s)

def test_fail_discover():
	""" This function will discover cases when operations throws exceptions for valid input """

	print(
		'from tru.gfx.thumbs import Operations\n'
		'from PIL import Image\n'
		'\n'
		'def test_discover_full():\n'
	)

	def try_oper(op_name, params, img_size):
		oper = getattr(Operations, op_name)
		try:
			img = Image.new('RGBa', img_size, color=(0,0,0,0))
			res = oper(*params)(img)
			#write_test(op_name, params, img.size, res.size)
		except:
			#print('\t# FAIL {} {} {}', op_name, params, img_size)
			write_test(op_name, params, img.size, 'FAIL')


	for img_size in range2(100, 100):
		for params in range2(100, 100):
			try_oper('FitWidth', params, img_size)






test_fail_discover()

