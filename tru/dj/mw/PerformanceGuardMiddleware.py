# -*- coding: utf-8 -*-

import time
import logging
from .CatchExceptions import CatchExceptions
from ..WebExceptions import BotRequestException

TLR_ban_started = None
TLR_counter = None
TLR_check_start = None

log = logging.getLogger(__name__)


def PerformanceGuardMiddleware(get_response):

	def process_request(request):
		global TLR_ban_started
		global TLR_counter
		global TLR_check_start

		__begin = time.time()

		ctrl_instance, action_method, func = request._routes_adapter

		if TLR_ban_started is not None:
			if __begin - TLR_ban_started > 2*60:
				TLR_ban_started = None
				log.error("Zakończenie blokowania BOTów")
			else:
				if request.IsBot or getattr(func, 'expensive_content', False):
					raise BotRequestException

		response = get_response(request)
		__end = time.time()

		if __end-__begin > 3.0 and TLR_ban_started is None:
			if TLR_check_start is None or __end - TLR_check_start > 15.0:
				TLR_counter = 0
				TLR_check_start = __end

			TLR_counter += 1

			# Przynajmniej 10 requestów w ciągu ostatnich 15sec trwało dłużej niż 3s → przeciążenie systemu.
			if TLR_counter > 10:
				TLR_ban_started = __end
				log.error("Rozpoczęcie blokowania BOTów")

		return response

	return process_request

