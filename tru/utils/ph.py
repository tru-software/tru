import requests
import json

class Ph:
	def __init__(self, url, token):
		self.url = url
		self.token = token

class PhError(Exception):
	pass


def ph_request_result(url, data):
	resp = requests.post(url, data)
	if resp.status_code == 200:
		resp = resp.json()
		if resp.get('error_code'):
			raise PhError("{}; {}".format(resp['error_code'], resp.get('error_info', '')))
	else:
		raise PhError("{}; http error code returned".format(resp.status_code))
	return resp['result']


def ph_request_data(url, data):
	data['limit'] = 100
	for i in range(10):
		result = ph_request_result(url, data)
		data['after'] = result['cursor']['after']
		for x in result['data']:
			yield x
		if not data['after']:
			break

	if data['after']:
		# more than 1000 results
		raise PhError("too much results")


def ph_upload_file_get_id(ph, name, data_base64, viewPolicy, canCDN):

	phid = ph_request_result(ph.url + 'file.upload', {
		'api.token': ph.token,
		'data_base64': data_base64,
		'name': name,
		'viewPolicy': viewPolicy, 
		'canCDN': canCDN,
	})

	data = list(ph_request_data(ph.url + 'file.search', {
		"api.token": ph.token,
		"constraints[phids][0]": phid,
	}))

	if len(data) != 1:
		raise PhError("expected one result")
	
	return data[0]['id']
