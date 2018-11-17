from tru.gfx.thumbs import Operations
from PIL import Image, ImageChops
import pytest
from random import randint

# import pytest; pytest.set_trace()

def check(oper, params, img_size, res_size):
	img = Image.new('RGBa', img_size, color=(0,0,0,0))
	op = Operations.FitWidth(*params)
	res = op(img)
	assert res.size == res_size
	assert op.GetFinalSize(*img_size) == res_size


def test_fit_width_1():
	# regression
	check(Operations.FitWidth, (1,0), img_size = (400,0), res_size = (1,1))

def test_fit_width_2():
	# regression
	check(Operations.FitWidth, (1,1), img_size = (400,4), res_size = (1,1))

def test_fit_width_3():
	# regression
	check(Operations.FitWidth, (1,1), img_size = (4,400), res_size = (1,1))

def test_fit_width_4():
	# regression
	check(Operations.FitWidth, (2,1), img_size = (4,400), res_size = (1,1))


def test_fit_all_1():
	check(Operations.FitAll, (100,300), img_size = (400,200), res_size = (100,50))

def test_fit_all_2():
	check(Operations.FitAll, (500,25), img_size = (400,200), res_size = (50,25))

def test_fit_all_3():
	check(Operations.FitAll, (4,2), img_size = (400,200), res_size = (4,2))

def test_fit_all_4():
	check(Operations.FitAll, (1,1), img_size = (400,200), res_size = (1,1))

def test_fit_all_5():
	check(Operations.FitAll, (0,0), img_size = (400,200), res_size = (400,200))

def test_fit_all_6():
	check(Operations.FitAll, (100,400), img_size = (100,600), res_size = (100,400))

def test_fit_all_7():
	check(Operations.FitAll, (400,100), img_size = (600,100), res_size = (400,100))
