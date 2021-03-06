def parse_page_number(string, maxv=None, minv=1):
	if not string:
		return minv
	string = str(string)
	if string and string.isdigit():
		page = int(string)
		if maxv:
			return min(maxv, max(minv, page))
		else:
			return max(minv, page)
	else:
		return minv
