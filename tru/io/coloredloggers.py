# -*- coding: utf-8 -*-

import logging

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter

formatter = TerminalFormatter()
lexer = get_lexer_by_name("pytb", stripall=True)


class ColoredExceptionFormatter(logging.Formatter):
	def formatException(self, exc_info):
		result = super(ColoredExceptionFormatter, self).formatException(exc_info)
		return highlight(result, lexer, formatter)
