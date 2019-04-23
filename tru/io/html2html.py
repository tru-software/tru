import sys
import re
# import tidy

from bs4 import BeautifulSoup, Tag, NavigableString, Comment, Declaration, ProcessingInstruction, CData

# ------------------------------------------------------------------------

class Filter:
	
	parse_unknown = False

	def check(self, tag):
		return self.tag(tag, tag.attrs)

	def tag(self, tag, attr):
		if tag.name not in self.tags:
			if self.parse_unknown is True:
				return None

			return False

		d = self.tags[tag.name]

		for a, k in list(attr.items()):
			try:
				if not d or (a in d) is False:
					del tag[a]
				elif d[a] is not None and d[a](k) is False:
					del tag[a]
			except AttributeError:
				del tag[a]

		return True

	def parse_style(self, style):
		css = []
		for c in style.split(';'):
			v = c.split(':')
			if len(v) != 2:
				continue
			css.append((v[0].strip(), v[1].strip()))
		return css

	def clean(self, soup):
		for e in soup.contents[:]:
			self.clean_part(e)

	def clean_part(self, node):
		if isinstance(node, (Comment, Declaration, ProcessingInstruction, CData)):
			node.extract()
		elif isinstance(node, NavigableString):
			pass
		elif isinstance(node, Tag):

			x = self.check(node)
			if x is False:
				node.extract()
			else:
				for e in node.contents[:]:
					self.clean_part(e)

				if x is None:
					i = node.parent.contents.index(node)+1
					for e in node.contents[:]:
						node.parent.insert(i, e)
					node.extract()

# ------------------------------------------------------------------------

class BasicFilter(Filter):

	def __init__(self):
		self.tags = {'strong':None, 'b':None, 'u':None, 'i':None, 'em':None, 'p':None}

# ------------------------------------------------------------------------

class PagerFilter(Filter):
	def __init__(self):
		self.tags = {}
		self.pages = []
	
	def clean(self, soup):
		self.pages.append('')
		for e in soup.contents:
			if isinstance(e,Tag) and e.name == 'div' and e.attrs.get('style') == 'page-break-after: always;':
				self.pages.append('')
			else:
				self.pages[-1] += e.__str__()

# ------------------------------------------------------------------------

class CommentFilter(Filter):
	def __init__(self):
		self.tags = {
			'a':{'href':None},
			'b':None,
			'strong':None,
			'u':None,
			'i':None,
			'em':None,
			'p':None,
			'blockquote':None,
		}

# ------------------------------------------------------------------------

class BlogFilter(Filter):

	def __init__(self):
		# wszystkie znaczniki z edytorka html
		self.tags = {
			'a':{'href':None},
			's':{'class':None},
			'b':{'class':None},
			'ol':{'class':None},
			'ul':{'class':None},
			'table':None,
			'h1':{'class':None},
			'h2':{'class':None},
			'h3':{'class':None},
			'h4':{'class':None},
			'h5':{'class':None},
			'h6':{'class':None},
			'td':{'class':None},
			'tr':{'class':None},
			'address':{'class':None},
			'strong':{'class':None},
			'q':{'class':None},
			'cite':{'class':None},
			'kbd':{'class':None},
			'var':{'class':None},
			'ins':{'class':None},
			'del':{'class':None},
			'samp':{'class':None},
			'pre':{'class':None},
			'div':{'class':None},
			'code':{'class':None},
			'li':{'class':None},
			'br':None,
			'strong':{'class':None},
			'u':None,
			'i':None,
			'em':None,
			'p':{'class':None, 'style':None},
			'blockquote':None,
			'img':{
				'src':None,
				'width':lambda v: v.isdigit() and int(v) >= 2 and int(v) < 530,
				'height':lambda v: v.isdigit() and int(v) >= 2 and int(v) < 530,
				'alt':None
			},
			'span':{'style':self._span_styles,'class':None}
		}
	
	@staticmethod
	def _is_color(value):
		return re.match( r'^rgb *\( *[0-9]{1,3} *, *[0-9]{1,3} *, *[0-9]{1,3} *\)$', value) is not None or \
			re.match( r'^#[0-9a-fA-F]{3}$', value) is not None or \
			re.match( r'^#[0-9a-fA-F]{6}$', value) is not None
	
	def _span_styles(self, style):
		css = self.parse_style(style)
		
		for n,v in css:
			# print "style: '%s'='%s'" % (n,v)
			if n == 'font-size':
				if not v in ('xx-large', 'x-large', 'large', 'medium', 'small', 'x-small', 'xx-small', 'larger', 'smaller'):
					return False
			elif n == 'color':
				if self._is_color(v) is not True:
					return False
			else:
				return False
		return True

# ------------------------------------------------------------------------

class HTMLCleaner:

	def parse( self, code, filter = None ):

		if filter is None:
			filter = BasicFilter()

		soup = BeautifulSoup(code, "html.parser")
		filter.clean(soup)
		# return soup.prettify(encoding=None);
		return soup.__str__()

# ------------------------------------------------------------------------

class HTMLPager:

	def parse( self, code ):

		filter = PagerFilter()
		soup = BeautifulSoup(code, "html.parser")
		filter.clean(soup)
		return filter.pages

if __name__ == "__main__":
	c = HTMLCleaner()
#	print c.parse( '<a href="xx"> dupa <b> dupa </b> dupa </a> <img src="dupa" width="2"/>', BlogFilter() )
#	print c.parse( '<span style="font-size:small; font-size : larger ">XXX</span>', BlogFilter() )
#	print c.parse( '<p><span style="color: rgb(51, 51, 0);color:#A00000;">asdasdasd</span></p>', BlogFilter() )
#	print c.parse( '<b>A<h1>B</h1>C</b>', BasicFilter() )

# ------------------------------------------------------------------------

def cleanup_xhtml(content, strip_comments=False):

	soup = BeautifulSoup(content, 'lxml')
	comments = soup.findAll(text=lambda text: isinstance(text, Comment))
	[comment.extract() for comment in comments]
	return str(soup)

	content = content.encode('utf8') if isinstance(content, str) else content

	# http://tidy.sourceforge.net/docs/quickref.html
	return str(tidy.parseString(content,
		output_xhtml=1,
		wrap=0,
		hide_comments=strip_comments,
		clean=0,
		indent=0,
		tidy_mark=0,
		quote_marks=1,
		show_body_only='auto',
		output_encoding='utf8',
		input_encoding='utf8'
	))
