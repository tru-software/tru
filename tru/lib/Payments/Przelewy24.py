# -*- coding: utf-8 -*-

## Dokumentacja:
# http://www.przelewy24.pl/files/cms/2/przelewy24_specyfikacja.pdf
# http://www.przelewy24.pl/files/cms/13/przelewy24_specification.pdf
# http://www.przelewy24.pl/files/cms/2/przelewy24_specyfikacja_3.01.pdf

import netaddr
import hashlib
import logging
import requests
import urllib

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


class Przelewy24Id(object):

	PRZELEWY24_URL_QA = 'https://sandbox.przelewy24.pl'
	PRZELEWY24_URL_PROD = 'https://secure.przelewy24.pl'
	PRZELEWY24_ID = None  # TODO: uzuepłnij
	PRZELEWY24_CRC = None  # TODO: uzuepłnij
	PRZELEWY24_ADDRS = [
		list(netaddr.iter_iprange('217.168.139.48', '217.168.139.55')),  # 217.168.139.48/29
		list(netaddr.iter_iprange('217.168.128.198', '217.168.128.202')),  # 217.168.128.198/31  217.168.128.200/31  217.168.128.202/32
		list(netaddr.iter_iprange('91.216.191.181', '91.216.191.185'))  # 91.216.191.181/32  91.216.191.182/31  91.216.191.184/31
	]

	def __init__(self, merchant_id, crc, qa=True):
		self.PRZELEWY24_ID = merchant_id
		self.PRZELEWY24_CRC = crc
		self.PRZELEWY24_URL = self.PRZELEWY24_URL_QA if qa else self.PRZELEWY24_URL_PROD

	def CRC(self, *fields):
		# print '|'.join(map(str, fields+(self.PRZELEWY24_CRC,) ))
		return hashlib.md5(('|'.join(map(str, fields+(self.PRZELEWY24_CRC,))).encode('utf8'))).hexdigest()

	@classmethod
	def VerifyRemoteAddr(cls, addr):
		addr = netaddr.IPAddress(addr)
		for i in cls.PRZELEWY24_ADDRS:
			if addr in i:
				return True
		return False

	def PaymentForm(self, *args, **kwargs):
		return PaymentForm(self, *args, **kwargs)

	def SuccessResponse(self, *args, **kwargs):
		return SuccessResponse(self, *args, **kwargs)

	def ErrorResponse(self, *args, **kwargs):
		return ErrorResponse(self, *args, **kwargs)


class PaymentForm:

	def __init__(self, p24: Przelewy24Id, description: str, order, url_return: str, url_cancel: str, url_cb: str, currency='PLN', country='PL'):

		self.p24 = p24
		self.description = description
		self.session_key = order.session_key
		self.email = order.owner_email
		self.url_return = url_return
		self.url_cancel = url_cancel
		self.url_cb = url_cb
		self.price = order.price
		self.currency = currency
		self.country = country

	def GetURL(self):
		return self.p24.PRZELEWY24_URL + '/trnDirect'

	def GetFields(self):
		return {
			"p24_api_version" : "3.2",
			"p24_merchant_id" : self.p24.PRZELEWY24_ID,
			"p24_pos_id"      : self.p24.PRZELEWY24_ID,
			"p24_session_id"  : self.session_key,
			"p24_amount"      : self.price,
			"p24_currency"    : self.currency,
			# "p24_description" : "TEST_ERR04",
			"p24_description" : self.description,
			"p24_email"       : self.email or 'at@tru.pl',
			"p24_country"     : self.country,
			"p24_url_return"  : self.url_return,
			"p24_url_cancel"  : self.url_cancel,
			"p24_url_status"  : self.url_cb,
			"p24_encoding"    : "UTF-8",
			"p24_sign"        : self.p24.CRC(self.session_key, self.p24.PRZELEWY24_ID, self.price, self.currency),
		}


class SuccessResponse:

	def __init__(self, p24: Przelewy24Id, P: dict):

		self.p24 = p24
		# print "Otrzymane dane: {}".format(P)
		# print "Scalone dane: {}".format( '|'.join(map(str, (P['p24_session_id'], P['p24_order_id'], P['p24_amount'], P['p24_currency'], self.PRZELEWY24_CRC) )) )
		# print "Klucz: {}".format( hashlib.md5('|'.join(map(str, (P['p24_session_id'], P['p24_order_id'], P['p24_amount'], P['p24_currency'], self.PRZELEWY24_CRC) )) ).hexdigest() )

		if P['p24_sign'] != self.p24.CRC(P['p24_session_id'], P['p24_order_id'], P['p24_amount'], P['p24_currency']):
			raise InputDataException( 'Nieprawidłowa suma kontrolna' )

		if str(P['p24_merchant_id']) != str(self.p24.PRZELEWY24_ID):
			raise InputDataException( 'Nieprawidłowy identyfikator sprzedawcy {}'.format(P['p24_merchant_id']) )

		self.merchant_id = int(P['p24_merchant_id'])
		self.session_key = P['p24_session_id']
		self.order_id = int(P['p24_order_id']) if P.get('p24_order_id') else None
		self.amount = int(P['p24_amount'])
		self.currency = P['p24_currency']

	def GetSessionKey(self):
		return self.session_key

	def Request(self, url, data):
		log.info("Payment verification: {}: {}".format(url, data))
		try:
			response = requests.post(url, data=data, verify=True)
		except requests.exceptions.RequestException as ex:
			log.error( "Payment verification: connection problem: {}".format(ex))
			raise VerifyConnectionException('Nie można połączyć w celu weryfikacji {}'.format(ex))

		log.info("Payment verification: Got response: {}".format(response.status_code))

		if response.status_code != 200:
			log.error( "Payment verification: invalid response: {}: {}".format(response.status_code, response.content))
			raise VerifyContentException('Nieprawidłowa odpowiedź: {}: {}'.format(response.status_code, response.content))

		return response.content.decode('utf8')

	def Verify(self):

		data = self.GetData()

		#Odpowiedź dla transakcji poprawnie zweryfikowanej:
		#error=0
		#Odpowiedź z błędem:
		#error={KOD_BŁĘDU}&errorMessage=field1:desc1&field1:desc2...
		#errorMessage może zawierać informacje dotyczące wielu błędów.

		#przychodzi też potwierdzenie w formacie: "RESULT\r\nTRUE" - być może to dotyczy starych transakcji

		verify_url = self.p24.PRZELEWY24_URL + '/trnVerify'
		content = self.Request(verify_url, data)

		log.info("Payment verification \"{}\": checking text: {}".format(verify_url, repr(content)))

		if not content:
			raise VerifyErrorException('ERROR', 'Empty response')

		if content.startswith('RESULT\r\n'):
			content = content[8:]
			if content == 'TRUE':
				return True

			VerifyErrorException(content, '')
		else:
			params = urllib.parse.parse_qs(content)

			if params.get('error') == '0':
				return True

			if content.strip() == 'error=0':
				return True

			raise VerifyErrorException(params.get('error'), params.get('errorMessage'))

	def GetOrderId(self):
		return self.order_id

	def GetData(self):
		return {
			"p24_merchant_id" : self.merchant_id,
			"p24_pos_id"      : self.merchant_id,
			"p24_session_id"  : self.session_key,
			"p24_amount"      : self.amount,
			"p24_currency"    : self.currency,
			"p24_order_id"    : self.order_id,
			"p24_sign"        : self.p24.CRC(self.session_key, self.order_id, self.amount, self.currency)
		}


class ErrorResponse:

	def __init__(self, p24: Przelewy24Id, P: dict):

		self.p24 = p24

		#if P['p24_crc'] != CRC( P['p24_session_id'], P['p24_order_id'], P['p24_kwota']):
		#	raise InputDataException( 'p24_crc', u'Nieprawidłowa suma kontrolna' )

		if str(P['p24_merchant_id']) != str(self.p24.PRZELEWY24_ID):
			raise InputDataException('p24_crc', 'Nieprawidłowy identyfikator sprzedawcy {}'.format(P['p24_merchant_id']))

		self.id_sprzedawcy = int(P['p24_merchant_id'])
		self.session_key = P['p24_session_id']
		self.order_id = int(P['p24_order_id'])
		self.amount = int(P['p24_amount'])

	def GetSessionKey(self):
		return self.session_key

	def GetOrderId(self):
		return self.order_id

