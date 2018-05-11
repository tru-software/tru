# -*- coding: utf-8 -*-

import logging


class MultilineSysLogHandler(logging.handlers.SysLogHandler):

	def format(self, record):
		msg = super(MultilineSysLogHandler, self).format(record)
		if isinstance(msg, bytes):
			return msg.decode('utf8')
		return msg

	def send_line(self, record, msg):

		if self.ident:
			msg = self.ident + msg
		if self.append_nul:
			msg += '\000'

		# We need to convert record level to lowercase, maybe this will
		# change in the future.
		prio = '<%d>' % self.encodePriority(self.facility,
											self.mapPriority(record.levelname))
		prio = prio.encode('utf-8')
		# Message is a string. Convert to bytes as required by RFC 5424
		msg = msg.encode('utf-8')
		msg = prio + msg
		if self.unixsocket:
			try:
				self.socket.send(msg)
			except OSError:
				self.socket.close()
				self._connect_unixsocket(self.address)
				self.socket.send(msg)
		elif self.socktype == socket.SOCK_DGRAM:
			self.socket.sendto(msg, self.address)
		else:
			self.socket.sendall(msg)


	def emit(self, record):
		"""
		Emit a record.
		The record is formatted, and then sent to the syslog server. If
		exception information is present, it is NOT sent to the server.
		"""
		try:
			msg = self.format(record)

			if '\n' not in msg:
				self.send_line(record, msg)
			else:
				record.message = ''
				prefix = (self.formatter or logging._defaultFormatter).formatMessage(record)
				for idx, i in enumerate(msg.split('\n')):
					if idx:
						i = '{}   + {: 2d}:   {}'.format(prefix, idx, i)
					self.send_line(record, i)

		except Exception:
			self.handleError(record)


logging.handlers.SysLogHandler = MultilineSysLogHandler
