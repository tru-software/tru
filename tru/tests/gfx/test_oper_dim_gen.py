from tru.gfx.thumbs import Operations
from PIL import Image, ImageChops
import pytest
from random import randint
from itertools import product
import random

def range2(w, h):
	for w in range(w):
		for h in range(h):
			yield (w,h)


vs0 = [0, 1, 3, 31, 91, 121]
vs1 = [   1, 3, 31, 91, 121]
cs0 = [0] + vs1 + [-v for v in vs1]


def test_FitWidth_dim():

	def test_operation(img, w, h):
		try:
			op = Operations.FitWidth(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)

			if not w:
				# noop
				assert res.size == img.size

			elif not h:
				# scale down to fit width
				assert res.size[0] <= w

				if w < img.size[0]:
					assert res.size[0] in [w, w-1]
				else:
					assert res.size == img.size

			else:
				# scale down
				assert res.size[0] <= w
				assert res.size[1] <= h

				if w < img.size[0] or h < img.size[1]:
					assert res.size[0] in [w,w-1] or res.size[1] in [h,h-1]
				else:
					assert res.size == img.size


		except:
			print("Operation FitWidth failed on {} -> {}".format(img.size, (w,h)))
			raise



	for img_size in product(vs1, vs1):
		img = Image.new('RGBa', img_size, color=(0,0,0,0))
		for wh in product(vs0, vs0):
			test_operation(img, *wh)



def test_FitAll_dim():

	def test_operation(img, w, h):
		try:
			op = Operations.FitAll(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)

			if not w or not h:
				assert res.size == img.size
			else:
				assert res.size[0] <= w
				assert res.size[1] <= h

				if w < img.size[0] or h < img.size[1]:
					assert res.size[0] in [w,w-1] or res.size[1] in [h,h-1]
				else:
					assert res.size == img.size

		except:
			print("Operation FitAll failed on {} -> {}".format(img.size, (w,h)))
			raise


	for img_size in product(vs1, vs1):
		img = Image.new('RGBa', img_size, color=(0,0,0,0))
		for wh in product(vs0, vs0):
			test_operation(img, *wh)




def test_MaxBox_dim():

	def test_operation(img, w, h):
		try:
			op = Operations.MaxBox(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)

			if w and h:
				assert res.size[0] <= w
				assert res.size[1] <= h
			else:
				assert res.size == img.size

		except:
			print("Operation MaxBox failed on {} -> {}".format(img.size, (w,h)))
			raise

	for img_size in product(vs1, vs1):
		img = Image.new('RGBa', img_size, color=(0,0,0,0))
		for wh in product(vs0, vs0):
			test_operation(img, *wh)



def test_Force_dim():

	def test_operation(img, w, h):
		try:
			op = Operations.Force(w,h)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)


			if not (w and h) or img.size[0] <= w and img.size[1] <= h:
				assert res.size == img.size
			else:
				assert res.size == (w,h)


		except:
			print("Operation Force failed on {} -> {}".format(img.size, (w,h)))
			raise

	for img_size in product(vs1, vs1):
		img = Image.new('RGBa', img_size, color=(0,0,0,0))
		for wh in product(vs0, vs0):
			test_operation(img, *wh)



def test_Manual_dim():

	def test_operation(img, w, h, crop):
		try:
			op = Operations.Manual(w,h,crop)
			res = op(img)
			assert res.size == op.GetFinalSize(*img.size)

			if w and h:
				assert res.size[0] <= w
				assert res.size[1] <= h

				if crop is not None:
					cx, cy, cw, ch = crop
					if cw > 0 and ch > 0:
						assert res.size[0] <= cw
						assert res.size[1] <= ch
			else:
				assert res.size == img.size

		except:
			print("Operation Manual failed on {} -> {} {}".format(img.size, (w,h), crop))
			raise

	for img_size in product(vs1, vs1):
		img = Image.new('RGBa', img_size, color=(0,0,0,0))
		for wh in product(vs0, vs0):
			for _ in range(100):
				cx,cy = random.choice(cs0),random.choice(cs0)
				cw,ch = random.choice(cs0),random.choice(cs0)
				test_operation(img, *wh, (cx,cy,cw,ch))


