import logging

import magic

log = logging.getLogger(__name__)

# ------------------------------------------------------------------------
# https://github.com/ahupp/python-magic
# http://stackoverflow.com/questions/43580/how-to-find-the-mime-type-of-a-file-in-python
# http://docs.python.org/library/mimetools.html

# https://github.com/ahupp/python-magic


def GetMIME(filepath):

	try:
		return magic.from_file(str(filepath), mime=True)
	except IOError:
		return None

	return None

# ------------------------------------------------------------------------
