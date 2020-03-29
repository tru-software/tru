
from django.conf import settings
from django.http import HttpResponse


def XsSharing(get_response):

	XS_SHARING_ALLOWED_ORIGINS = settings.XS_SHARING_ALLOWED_ORIGINS
	XS_SHARING_ALLOWED_METHODS = ",".join(settings.XS_SHARING_ALLOWED_METHODS)

	def middleware(request):

		if 'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META:
			response = HttpResponse()
			response['Access-Control-Allow-Origin'] = XS_SHARING_ALLOWED_ORIGINS
			response['Access-Control-Allow-Methods'] = XS_SHARING_ALLOWED_METHODS
			return response

		response = get_response(request)

		response['Access-Control-Allow-Origin'] = XS_SHARING_ALLOWED_ORIGINS
		response['Access-Control-Allow-Methods'] = XS_SHARING_ALLOWED_METHODS

		return response

	return middleware

# ----------------------------------------------------------------------------
