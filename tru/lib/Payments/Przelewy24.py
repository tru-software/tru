# -*- coding: utf-8 -*-

## Dokumentacja:
# http://www.przelewy24.pl/files/cms/2/przelewy24_specyfikacja.pdf
# http://www.przelewy24.pl/files/cms/13/przelewy24_specification.pdf
# http://www.przelewy24.pl/files/cms/2/przelewy24_specyfikacja_3.01.pdf

import netaddr
import hashlib
import logging
import requests

log = logging.getLogger(__name__)

class Przelewy24Exception(Exception):
	pass


class InputDataException(Przelewy24Exception):
	pass


class VerifyConnectionException(Przelewy24Exception):
	pass


class VerifyContentException(Przelewy24Exception):
	pass


class VerifyErrorException(Przelewy24Exception):
	def __init__(self, error_code, message):
		super(VerifyErrorException, self).__init__(message)
		self.error_code = error_code


class Przelewy24(object):

	PRZELEWY24_URL = 'https://sandbox.przelewy24.pl'
	PRZELEWY24_ID = None  # TODO: uzuepłnij
	PRZELEWY24_CRC = None  # TODO: uzuepłnij
	PRZELEWY24_ADDRS = [
		list(netaddr.iter_iprange('217.168.139.48', '217.168.139.55')),  # 217.168.139.48/29
		list(netaddr.iter_iprange('217.168.128.198', '217.168.128.202')),  # 217.168.128.198/31  217.168.128.200/31  217.168.128.202/32
		list(netaddr.iter_iprange('91.216.191.181', '91.216.191.185'))  # 91.216.191.181/32  91.216.191.182/31  91.216.191.184/31
	]


	def CRC(self, *fields):
		# print '|'.join(map(str, fields+(self.PRZELEWY24_CRC,) ))
		return hashlib.md5(('|'.join(map(str, fields+(self.PRZELEWY24_CRC,))).encode('utf8'))).hexdigest()


class PaymentForm(Przelewy24):

	def __init__(self, merchant_id, crc, description, payment, url_return, url_cancel):

		self.PRZELEWY24_ID = merchant_id
		self.PRZELEWY24_CRC = crc
		self.description = description
		self.session_key = payment.session_key
		self.email = payment.owner_email
		self.url_return = url_return
		self.url_cancel = url_cancel
		self.price = payment.price

	def GetURL(self):
		return self.PRZELEWY24_URL + '/trnDirect'

	def GetFields(self):
		return {
			"p24_api_version" : "3.2",
			"p24_merchant_id" : self.PRZELEWY24_ID,
			"p24_pos_id"      : self.PRZELEWY24_ID,
			"p24_session_id"  : self.session_key,
			"p24_amount"      : self.price,
			"p24_currency"    : "PLN",
			# "p24_description" : "TEST_ERR04",
			"p24_description" : "Zakup produktów",
			"p24_email"       : self.email or 'at@tru.pl',
			"p24_country"     : "PL",
			"p24_url_return"  : self.url_return,
			"p24_url_cancel"  : self.url_cancel,
			"p24_encoding"    : "UTF-8",
			"p24_sign"        : self.CRC(self.session_key, self.PRZELEWY24_ID, self.price, 'PLN'),
		}


class SuccessResponse(Przelewy24):

	def __init__(self, P):

		super(SuccessResponse, self).__init__()

		# print "Otrzymane dane: {}".format(P)
		# print "Scalone dane: {}".format( '|'.join(map(str, (P['p24_session_id'], P['p24_order_id'], P['p24_amount'], P['p24_currency'], self.PRZELEWY24_CRC) )) )
		# print "Klucz: {}".format( hashlib.md5('|'.join(map(str, (P['p24_session_id'], P['p24_order_id'], P['p24_amount'], P['p24_currency'], self.PRZELEWY24_CRC) )) ).hexdigest() )

		if P['p24_sign'] != self.CRC( P['p24_session_id'], P['p24_order_id'], P['p24_amount'], P['p24_currency']):
			raise InputDataException( 'Nieprawidłowa suma kontrolna' )

		if str(P['p24_merchant_id']) != str(self.PRZELEWY24_ID):
			raise InputDataException( 'Nieprawidłowy identyfikator sprzedawcy {}'.format(P['p24_merchant_id']) )

		self.merchant_id = int(P['p24_merchant_id'])
		self.session_key = P['p24_session_id']
		self.order_id = int(P['p24_order_id'])
		self.amount = int(P['p24_amount'])

	def GetSessionKey(self):
		return self.session_key

	def Verify(self, payment):

		data = {
			"p24_merchant_id" : self.merchant_id,
			"p24_pos_id"      : self.merchant_id,
			"p24_session_id"  : self.session_key,
			# "p24_amount"      : self.amount,
			"p24_amount"      : payment.price,
			"p24_currency"    : 'PLN',
			"p24_order_id"    : self.order_id,
			"p24_sign"        : self.CRC( self.session_key, self.order_id, payment.price, 'PLN')
		}

		log.info( "Payment verification: {}: {}".format( self.PRZELEWY24_URL + '/trnVerify', data)  )
		try:
			response = requests.post( self.PRZELEWY24_URL + '/trnVerify', data=data, verify=True )
		except requests.exceptions.RequestException as ex:
			log.error( "Payment verification: connection problem: {}".format(ex))
			raise VerifyConnectionException( 'Nie można połączyć w celu weryfikacji {}'.format(ex) )

		log.info( "Payment verification: Got response: {}".format(response.status_code))

		if response.status_code != 200:
			log.error( "Payment verification: invalid response: {}: {}".format(response.status_code, response.content))
			raise VerifyContentException( 'Nieprawidłowa odpowiedź: {}: {}'.format(response.status_code, response.content) )

		content = response.text

		log.info( "Payment verification: checking text: {}".format(repr(content)))

		try:
			lines = iter(content.splitlines())
			while True:
				line = next(lines).strip()
				if line == 'RESULT':
					break

			line = next(lines).strip()

			if line == 'TRUE':
				return True
			elif line == 'ERR':
				error_code = next(lines).strip()
				message = next(lines).strip()
				raise VerifyErrorException(error_code, message)
		except StopIteration:
			pass

		raise VerifyContentException( 'Niezrozumiała odpowiedź: {}'.format(repr(content)) )

	def GetOrderId(self):
		return self.order_id

	def GetData(self):
		return {
			"p24_merchant_id" : self.merchant_id,
			"p24_pos_id"      : self.merchant_id,
			"p24_session_id"  : self.session_key,
			"p24_amount"      : self.amount,
			"p24_currency"    : 'PLN',
			"p24_order_id"    : self.order_id,
			"p24_sign"        : self.CRC( self.session_key, self.order_id, self.amount, 'PLN')
		}


class ErrorResponse(Przelewy24):

	def __init__(self, P):

		super(ErrorResponse, self).__init__()

		#if P['p24_crc'] != CRC( P['p24_session_id'], P['p24_order_id'], P['p24_kwota']):
		#	raise InputDataException( 'p24_crc', u'Nieprawidłowa suma kontrolna' )

		if str(P['p24_merchant_id']) != str(self.PRZELEWY24_ID):
			raise InputDataException( 'p24_crc', 'Nieprawidłowy identyfikator sprzedawcy {}'.format(P['p24_merchant_id']) )

		self.id_sprzedawcy = int(P['p24_merchant_id'])
		self.session_key = P['p24_session_id']
		self.order_id = int(P['p24_order_id'])
		self.amount = int(P['p24_amount'])

	def GetSessionKey(self):
		return self.session_key

	def GetOrderId(self):
		return self.order_id

