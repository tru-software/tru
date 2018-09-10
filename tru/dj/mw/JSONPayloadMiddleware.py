import json


def JSONPayloadMiddleware(get_response):

	def process_request(request):

		# "application/json"
		# "application/json; charset=utf-8"
		if request.content_type.startswith('application/json'):

			data = json.loads(request.body.decode("utf-8")) if request.body else None
			if request.method == 'POST':
				request.POST = data
			elif request.method == 'PUT':
				request.PUT = data

		response = get_response(request)

		return response

	return process_request
