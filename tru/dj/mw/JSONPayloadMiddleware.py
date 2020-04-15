import json
import logging

log = logging.getLogger(__name__)


def JSONPayloadMiddleware(get_response):

	def process_request(request):

		# "application/json"
		# "application/json; charset=utf-8"
		if request.content_type.startswith('application/json'):

			data = json.loads(request.body.decode("utf-8")) if request.body else {}
			if not isinstance(data, dict):
				# A root object of the JSON payload should be a dict, due to django expectation
				# for serialization of request.POST, for example here:
				# site-packages/django/views/debug.py", line 305, in get_traceback_data
				# 'filtered_POST_items': list(self.filter.get_post_parameters(self.request).items()),
				# AttributeError: 'NoneType' object has no attribute 'items'
				log.debug(f"Payload of {request.method} is not a dict: %s", data)

			if request.method == 'POST':
				request.POST = data
			elif request.method == 'PUT':
				request.PUT = data
			elif request.method == 'DELETE':
				request.DELETE = data

		response = get_response(request)

		return response

	return process_request
