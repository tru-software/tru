# -*- coding: utf-8 -*-

from django.conf import settings
import os.path

import email.utils
try:
	# Py3
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText
	from email.mime.image import MIMEImage
	import email.charset as Charset
except ImportError:
	# Py2
	from email.MIMEMultipart import MIMEMultipart
	from email.MIMEText import MIMEText
	from email.MIMEImage import MIMEImage
	from email import Charset

from smtplib import SMTP, SMTP_SSL

smtp_server=settings.EMAIL_HOST
smtp_port=settings.EMAIL_PORT
smtp_user=settings.EMAIL_HOST_USER
smtp_pass=settings.EMAIL_HOST_PASSWORD
smtp_tls=settings.EMAIL_USE_TLS
smtp_ssl=settings.EMAIL_USE_SSL

charset='utf-8'
Charset.add_charset(charset, Charset.SHORTEST, None, None)


class MailImageCollector:

	def __init__(self):
		self._images = {}
		self._cid    = 0

	def get_images(self):
		return list(self._images.items())

	def __call__(self, image_file_name):

		if image_file_name.startswith(settings.UPLOAD_URL):
			abs_path = settings.UPLOAD_DIR + image_file_name[len(settings.UPLOAD_URL):]
		else:
			abs_path = settings.BASE_DIR_FRONTEND + image_file_name

		if abs_path in self._images:
			return self._images[abs_path]

		if not os.path.isfile( abs_path ):
			return ''

		self._cid = self._cid + 1
		new_cid = 'img_%d'%self._cid
		self._images[abs_path] = new_cid

		return 'cid:%s'%new_cid

# ----------------------------------------------------------------------------

def send_mail(subject, email, request, env, html_part, text_part='', from_field=settings.EMAIL_DEFAULT_FROM, reply_to=None):

	image_collector = MailImageCollector()

	# my_ucr = email_ucr( image_collector )
	if callable(html_part):
		# env = html_part.env
		# env['ucr'] = my_ucr
		# if 'request' in env:
		#       env['request'].ucr = my_ucr

		html_part = html_part( request, dict(GENERATE_HTML_CONTENT=True, **env) ).content.strip()
		# s = BeautifulSoup(html_part)
		# html_part = s.renderContents(encoding=None, prettyPrint=False)

	if callable(text_part):
		text_part = text_part( request, dict(GENERATE_HTML_CONTENT=False, **env) ).content.strip()

	if settings.DEBUG:
		print('-------------------------------------')
		print(html_part)
		print('-------------------------------------')
		print(text_part)
		print('-------------------------------------')
		print([ i for i in list(image_collector._images.items()) ])

	send_html_mail(subject, html_part, text_part, email, images = image_collector.get_images(), from_=from_field, reply_to=reply_to )

# ----------------------------------------------------------------------------

def send_html_mail(subject,html_content,text_content,to_,from_=settings.EMAIL_DEFAULT_FROM,images=(),reply_to=None,files=None):
	'''
	if you want to use Django template system:
		use `msg` and optionally `textmsg` as template context (dict)
		and define `template` and optionally `texttemplate` variables.
	otherwise msg and textmsg variables are used as html and text message sources.
	
	if you want to use images in html message, define physical paths and ids in tuples.
	(image paths are relative to  MEDIA_ROOT)
	example: 
	images=(('email_images/logo.gif','img1'),('email_images/footer.gif','img2'))
	and use them in html like this:
	<img src="cid:img1">
	...
	<img src="cid:img2">
	'''

	msgRoot = MIMEMultipart('related')
	msgRoot['Subject'] = subject
	msgRoot['From'] = from_
	msgRoot['To'] =  to_
	msgRoot['Date'] = email.utils.formatdate()
	if reply_to:
		msgRoot['Reply-To'] =  reply_to
		msgRoot['Mail-Reply-To'] =  reply_to
		msgRoot['Mail-Followup-To'] =  reply_to
	msgRoot.preamble = 'This is a multi-part message in MIME format.'

	msgAlternative = MIMEMultipart('alternative')
	msgRoot.attach(msgAlternative)

	if isinstance(text_content, str):
		text_content = text_content.encode(charset)

	if isinstance(html_content, str):
		html_content = html_content.encode(charset)

	if text_content:
		msgAlternative.attach(MIMEText(text_content, _charset=charset))

	if html_content:
		msgAlternative.attach(MIMEText(html_content, 'html', _charset=charset))

	if images:
		for img in images:
			with open(img[0], 'rb') as fp:
				msgImage = MIMEImage(fp.read())
				msgImage.add_header('Content-ID', '<'+img[1]+'>')
				msgRoot.attach(msgImage)

	if files:
		for path, mimetype, filename in files:
			fileMsg = email.mime.base.MIMEBase(*mimetype.split('/'))
			with open(path, 'rb') as fp:
				fileMsg.set_payload(fp.read())
				email.encoders.encode_base64(fileMsg)
				fileMsg.add_header('Content-Disposition','attachment;filename={}'.format(filename or os.path.basename(path)))
				msgRoot.attach(fileMsg)
	
	smtp = SMTP(smtp_server, smtp_port) if smtp_ssl is not True else SMTP_SSL(smtp_server, smtp_port)
	smtp.ehlo()
	if smtp_tls and not smtp_ssl:
		smtp.starttls()
		smtp.ehlo()
	if smtp_user:
		smtp.login(smtp_user, smtp_pass)
	smtp.sendmail(from_, to_, msgRoot.as_string())
	smtp.quit()
