import pytest
from tru.gfx.thumbs import Operations
from PIL import Image

# import pytest; pytest.set_trace()

def check(oper, params, img_size, res_size):
	img = Image.new('RGBa', img_size, color=(0,0,0,0))
	op = oper(*params)
	res = op(img)
	assert res.size == res_size
	assert op.GetFinalSize(*img_size) == res_size


def test_fit_width_1():
	# regression
	check(Operations.FitWidth, (1,0), img_size = (400,0), res_size = (1,1))

def test_fit_width_2():
	# regression
	check(Operations.FitWidth, (1,1), img_size = (400,4), res_size = (1,1))
	check(Operations.FitWidth, (1,1), img_size = (4,400), res_size = (1,1))

def test_fit_width_3():
	# regression
	check(Operations.FitWidth, (2,1), img_size = (4,400), res_size = (1,1))


def test_fit_all_1():
	check(Operations.FitAll, (100,300), img_size = (400,200), res_size = (100,300))

def test_fit_all_2():
	check(Operations.FitAll, (500,25), img_size = (400,200), res_size = (500,25))

def test_fit_all_3():
	check(Operations.FitAll, (4,2), img_size = (400,200), res_size = (4,2))

def test_fit_all_4():
	check(Operations.FitAll, (1,1), img_size = (400,200), res_size = (1,1))

def test_fit_all_5():
	check(Operations.FitAll, (0,0), img_size = (400,200), res_size = (400,200))

def test_fit_all_6():
	check(Operations.FitAll, (100,400), img_size = (100,600), res_size = (100, 400))

def test_fit_all_7():
	check(Operations.FitAll, (400,100), img_size = (600,100), res_size = (400, 100))


def test_max_box_1():
	check(Operations.MaxBox, (0,0), img_size = (5,3), res_size = (5,3))

def test_max_box_2():
	check(Operations.MaxBox, (1,0), img_size = (5,3), res_size = (5,3))
	check(Operations.MaxBox, (0,1), img_size = (5,3), res_size = (5,3))

def test_max_box_3():
	# regression
	check(Operations.MaxBox, (1,1), img_size = (1, 1000), res_size = (1, 1))
	check(Operations.MaxBox, (1,1), img_size = (1000, 1), res_size = (1, 1))

def test_max_box_4():
	check(Operations.MaxBox, (100,100), img_size = (1000,500), res_size = (100, 50))
	check(Operations.MaxBox, (100,100), img_size = (500,1000), res_size = (50, 100))



def test_force_1():
	# regression
	check(Operations.Force, (100,100), img_size = (50,150), res_size = (100, 100))
	check(Operations.Force, (100,100), img_size = (150,50), res_size = (100, 100))



def test_manual_1():
	check(Operations.Manual, (100,100,(0,0,0,0)), img_size = (50,150), res_size = (100, 100))

def test_manual_2():
	# regression
	check(Operations.Manual, (100,100,(10,10,150,150)), img_size = (150,150), res_size = (90, 90))

def test_manual_3():
	check(Operations.Manual, (100,100,(10,10,20,30)), img_size = (50,150), res_size = (20, 30))
