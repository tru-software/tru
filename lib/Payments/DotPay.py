# -*- coding: utf-8 -*-

import netaddr
import hashlib
import logging
import requests

log = logging.getLogger(__name__)


class DotPayException(Exception):
	pass


class InputDataException(DotPayException):
	pass


class VerifyConnectionException(DotPayException):
	pass


class VerifyContentException(DotPayException):
	pass


class VerifyErrorException(DotPayException):
	def __init__(self, error_code, message):
		super(VerifyErrorException, self).__init__(message)
		self.error_code = error_code


class DotPay(object):

	class Statuses:

		New = "new"
		Processing = "processing"
		Completed = "completed"
		Rejected = "rejected"
		ProcessingRealizationWaiting = "processing_realization_waiting"
		ProcessingRealization = "processing_realization"

		names = {
			New: u"nowa",
			Processing: u"przetwarzana",
			Completed: u"wykonana",
			Rejected: u"odrzucona",
			ProcessingRealizationWaiting: u"oczekuje na realizację",
			ProcessingRealization: u"realizowana",
		}

	DOTPAY_URL = 'https://ssl.dotpay.pl/t2/'
	DOTPAY_URL_TEST = 'https://ssl.dotpay.pl/test_payment/'
	DOTPAY_ID = ''
	DOTPAY_CRC = ''
	DOTPAY_ADDRS = [
		list(netaddr.iter_iprange('195.150.9.37', '195.150.9.37'))
	]

	DOTPAY_ERRORS = {
		"PAYMENT_EXPIRED": "przekroczona data ważności wygenerowanego linku płatniczego lub przekazana w parametrze expiration_date",
		"UNKNOWN_CHANNEL": "nieznany kanał",
		"DISABLED_CHANNEL": "wyłączony kanał płatności",
		"BLOCKED_ACCOUNT": "zablokowane konto",
		"INACTIVE_SELLER": "brak możliwości dokonania płatności spowodowany brakiem aktywacja konta",
		"AMOUNT_TOO_LOW": "mniejsza kwota niż minimalna określona dla sklepu",
		"AMOUNT_TOO_HIGH": "większa kwota niż maksymalna określona dla sklepu",
		"BAD_DATA_FORMAT": "przesłano błędny format danych np. błędny format parametru expiration_date",
		"UNKNOWN_ERROR": "wartość zwracana w innym przypadku niż powyższe",
	}

	CRC_FIELDS = ("id,operation_number,operation_type,operation_status,operation_amount,operation_currency,"+
			"operation_withdrawal_amount,operation_commission_amount,operation_original_amount,operation_original_currency,"+
			"operation_datetime,operation_related_number,control,description,email,p_info,p_email,channel,channel_country,geoip_country").split(",")

	def CRC(self, pin, fields):
		return hashlib.sha256((pin + "".join(fields.get(i, '') for i in self.CRC_FIELDS)).encode('utf8')).hexdigest()

	@classmethod
	def VerifyRemoteAddr(cls, addr):
		addr = netaddr.IPAddress(addr)
		for i in cls.DOTPAY_ADDRS:
			if addr in i:
				return True
		return False


class PaymentForm(DotPay):

	def __init__(self, account_id, description, payment, url_return, url_callback):

		self.account_id = account_id
		self.session_key = payment.session_key
		self.email = payment.owner_email
		self.url_return = url_return
		self.url_callback = url_callback
		self.price = payment.price
		self.description = description
		self.payment = payment

	def GetURL(self, debug=True):
		if debug:
			return self.DOTPAY_URL_TEST
		return self.DOTPAY_URL

	def GetFields(self):
		"""
			"street_n1" # Numer budynku.
			"street_n2" # Numer mieszkania/lokalu.
			"postcode"
			"phone"

			"p_info"
				Nazwa odbiorcy płatności, która zostanie wyświetlona Klientowi na stronie
				płatności serwisu Dotpay. W przypadku nieprzesłania parametru wyświetlona
				zostanie domyślna nazwa sklepu widoczna w panelu administracyjnym Dotpay.
				typ: string
				maksymalna długość: 300
				Przykład: p_info=Sklep www.example.com

			"p_email"
				Adres e-mail, który zostanie wyświetlony Kupującemu w celu kontaktu ze
				Sprzedawcą. Przesłanie parametru nadpisuje domyślny adres sklepu podany
				podczas rejestracji w serwisie Dotpay.
				typ: string
				maksymalna długość: 100
				Przykład: p_email=biuro@example.com
		"""

		return {
			"id"              : self.account_id,
			"currency"        : "PLN",
			"description"     : self.description,
			"amount"          : "{}.{}".format(int(self.price/100), self.price%100),

			"api_version"     : "dev",
			"lang"            : "pl",
			"country"         : "PL",
			"type"            : 3, # URL + URLC
			"url"             : self.url_return,
			"urlc"            : self.url_callback,

			"buttontext"      : u"Powrót do serwisu",
			"control"         : self.session_key,

			"firstname"       : self.payment.GetUserData('first'),
			"lastname"        : self.payment.GetUserData('last'),
			"email"           : self.payment.GetUserData('mail'),
			"street"          : self.payment.GetUserData('street'),
			"postcode"        : self.payment.GetUserData('postcode'),
			"city"            : self.payment.GetUserData('city')
		}


class SuccessResponse(DotPay):

	def __init__(self, acconut_id, pin, payment, DEBUG):

		super(SuccessResponse, self).__init__()

		self.acconut_id = acconut_id
		self.pin = pin
		self.payment = payment
		self.DEBUG = DEBUG

	def Verify(self, request, P):

		if not self.DEBUG:
			signature = self.CRC(self.pin, P)
			if P['signature'] != signature:
				raise InputDataException(u'Nieprawidłowa suma kontrolna "{}" != "{}"'.format(P['signature'], signature))

		if str(P['id']) != str(self.acconut_id):
			raise InputDataException(u'Nieprawidłowy identyfikator sprzedawcy {}'.format(P['id']))

		if P['control'] != self.payment.session_key:
			raise InputDataException(u'Nieprawidłowy identyfikator sessji "{}" != "{}"'.format(P['control'], self.payment.session_key))

		# operation_original_amount == "{}.{}".format(int(self.price/100), self.price%100)

		status = P['operation_status']

		if status not in self.Statuses.names:
			raise InputDataException(u'Nieprawidłowy stan operacji: {}'.format(status))

		Statuses = DotPay.Statuses
		if status == Statuses.New:
			pass
		elif status in (Statuses.Processing, Statuses.ProcessingRealizationWaiting, Statuses.ProcessingRealization):
			self.payment.SetProcessing(request, P)
		elif status == Statuses.Completed:
			self.payment.SetVerified(request, P)
		elif status == Statuses.Rejected:
			self.payment.SetVerifyError(request, P)
		else:
			self.payment.SetInvalidStatus(request, P)

		return True

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
			"p24_sign"        : self.CRC(self.session_key, self.order_id, self.amount, 'PLN')
		}


class ErrorResponse(DotPay):

	def __init__(self, P):

		super(ErrorResponse, self).__init__()

		#if P['p24_crc'] != CRC( P['p24_session_id'], P['p24_order_id'], P['p24_kwota']):
		#	raise InputDataException(u'Nieprawidłowa suma kontrolna' )

		if str(P['p24_merchant_id']) != str(self.DOTPAY_ID):
			raise InputDataException(u'Nieprawidłowy identyfikator sprzedawcy {}'.format(P['p24_merchant_id']) )

		self.id_sprzedawcy = int(P['p24_merchant_id'])
		self.session_key = P['p24_session_id']
		self.order_id = int(P['p24_order_id'])
		self.amount = int(P['p24_amount'])

	def GetSessionKey(self):
		return self.session_key

	def GetOrderId(self):
		return self.order_id

