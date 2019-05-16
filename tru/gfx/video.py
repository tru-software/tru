import datetime
import functools
import json
import logging
import mimetypes
import os
import random
import re
import shutil
import select
import subprocess
import sys
from io import BytesIO
from struct import pack, unpack
from base64 import urlsafe_b64decode, urlsafe_b64encode

from ..fs.utils import TmpFile, path_replace_ext
from ..io.hash import DecodeHash, Distribution, EncodeHash, Hash, coalesce, Hash32
from .thumbs import Operations

log = logging.getLogger(__name__)

# -------------------------------------------------------------------


class VideoFormat:

	formats = (
		# ID, MimeType, File Ext, ffmpeg -format
		(0x02, "video/mp4", "mp4", "mp4"), # MP4 (MPEG-4 Part 14)
		(0x03, "video/flv", "flv", "flv"),  # FLV (Flash Video)
		(0x04, "video/avi", "avi", "avi"),  # AVI (Audio Video Interleaved)
		(0x05, "video/wmv", "wmv", None),
		(0x06, "video/mov", "mov", "mov"),  # QuickTime / MOV
		(0x07, "video/mpg", "mpg", "mpeg"),  # MPEG-1 Systems / MPEG program stream
		(0x08, "video/3pg", "3pg", "3gp"),  # 3GP (3GPP file format)
		(0x09, "image/gif", "gif", "gif"),  # GIF Animation
	)

	formats_by_id = {tpl[0]: tpl for tpl in formats}
	formats_by_mimetype = {tpl[1]: tpl for tpl in formats}
	formats_by_ext = {tpl[2]: tpl for tpl in formats}


	def __init__(self, video_size, audio=None, format=None, fps=None, mimetype=None):
		self.video_size = video_size
		self.audio = audio
		self.format = format
		self.fps = fps
		self.mimetype = mimetype

	def get_params(self, dict=None):
		dict = dict if dict is not None else {}

		return dict

	class ThumbSize(object):

		op_code = None  # Overwrite!

		def get_params(self, d):
			pass

		def calcCropSizeFrom(self, w, h, best_case=False):
			return (w, h)

		def type_name(self):
			d={}
			self.get_params(d)
			return d['thumb_type']

		def get_size(self):
			return (None, None)

		def _getOpParams(self):
			return pack('!HH', self.w or 0, self.h or 0)

		def GetCropWithPoint(self, img_w, img_h, x, y):
			return None

		@classmethod
		def decode(cls, data):
			return cls(*unpack('!HH', data[:4]))

		@classmethod
		def FromParams(cls, params):
			return cls()

		def GetNoPictureSizeInts(self):
			return (77, 77)


	class Original(ThumbSize):

		op_code = 0x01

		def __init__(self):
			pass

		def get_params(self, d):
			d['thumb_type'] = 'Org'

		def __str__(self):
			return 'Bez zmian'

		def get_size(self):
			return (None, None)

		@classmethod
		def decode(cls, data):
			return cls()

		def _getOpParams(self):
			return pack('!B', 0x44)


	class MaxBox(ThumbSize, Operations.MaxBox):

		op_code = 0x02

		def __init__(self, cx, cy):
			super().__init__(cx, cy)

		def get_params(self, d):
			d['thumb_type'] = 'MaxBox'
			d['width'] = self.w
			d['height'] = self.h

		def calcCropSizeFrom(self, w, h, best_case=False):
			return self.GetFinalSize(w, h)

		def get_size(self):
			return (self.w, self.h)

		def __str__(self):
			return 'Całość do max: %sx%s' % (self.w, self.h)

		@classmethod
		def FromParams(cls, params):
			return cls(params['width'], params['height'])

		def GetNoPictureSizeInts(self):
			return self.w, self.h

	classes = [
		Original, MaxBox
	]
	classes_map = {i.op_code:i for i in classes}
	classes_map_by_name = {i.__name__:i for i in classes}
	classes_map_by_name['Org'] = Original

	url_fmt_re = re.compile('^[0-9a-zA-Z_\-=]+$')


	def Encode(self, filename, key, **kwargs):

		if ' ' in filename:
			raise ValueError("Encode source path with urlencode")

		assert isinstance(key, bytes), "Key must be an instance of bytes, got {}".format(repr(key))

		encoder_version = 0

		format_id = (self.formats_by_mimetype.get(self.format) or self.formats_by_id[0x02])[0]

		trx = pack('!BBBBB', encoder_version, format_id, self.video_size.op_code, self.audio or 0, self.fps or 0) + self.video_size._getOpParams()

		if (len(trx)+4) % 3:
			trx += pack('!B', 0) * (3-((len(trx)+4) % 3))

		# The filename here is a url-encoded path.
		trx_hash = Hash32(key + trx + filename.encode('ascii'))
		return urlsafe_b64encode(trx + pack('!I', trx_hash)).decode('ascii')


	@classmethod
	def Decode(cls, data, filename, key):

		assert isinstance(key, bytes), "Key must be an instance of bytes, got {}".format(repr(key))

		if not cls.url_fmt_re.match(data):
			raise ValueError('Invalid fmt data: {}'.format(data))

		filename = filename.encode('ascii') if isinstance(filename, str) else filename
		data = urlsafe_b64decode(data.encode('ascii') if isinstance(data, str) else data)

		encoder_version, = unpack('!B', data[:1])
		if encoder_version == 0:
			trx = data[:-4]
			org_hash = unpack('!I', data[-4:])[0]
			trx_hash = Hash32(key + trx + filename)
		else:
			raise ValueError(f'Invalid encoder version: {encoder_version}')

		if org_hash != trx_hash:
			raise ValueError('Invalid checksum')

		if encoder_version == 0:
			encoder_version, format_id, op_code, audio, fps = unpack('!BBBBB', trx[:5])
			video_size = cls.classes_map[op_code].decode(trx[5:])

		format_tpl = (cls.formats_by_id.get(format_id) or cls.formats_by_id[0x02])

		conv = cls(video_size=video_size, format=format_tpl[1], audio=audio or None, fps=fps or None)

		return conv


	def GetCmd(self, path):
		cmd = [
	        'ffmpeg',
			"-y",
	        '-i', path,
			'-sn',  # disable subtitle
			'-framerate', str(self.fps),  #  number     set the number of video frames to output
		]

		w, h = self.video_size.get_size()
		if w and h:
			cmd += ['-s', f'{w}x{h}']

		if not self.audio:
			cmd += ['-an']
		else:
			# TODO:
			# cmd += ['-q:a', str(self.audio)]
			cmd += ['-c:a', 'copy']

		format_tpl = self.formats_by_mimetype[self.format]
		ffmpeg_encoder = format_tpl[3]

		cmd += ['-f', ffmpeg_encoder]

		if self.format == "image/gif":
			# -t  - time limit
			# -ss - skip start seconds
			# setpts - speedup
			cmd += ['-t', '5', '-ss', '1', '-filter:v', "setpts=0.4*PTS"]
		else:
			# https://stackoverflow.com/questions/34123272/ffmpeg-transmux-mpegts-to-mp4-gives-error-muxer-does-not-support-non-seekable
			cmd += ['-c:v', 'copy']
			cmd += ['-movflags', 'frag_keyframe+empty_moov']

		cmd += ['pipe:1']

		return cmd

	def GetPath(self, path, postfix):
		ext = (self.formats_by_mimetype.get(self.format) or self.formats_by_id[0x02])[2]
		return path_replace_ext(path, ext, postfix)

	def GenerateAsStream(self, src_path, cmd, bs=1024*4):
		log.info("Generating video: {}".format(" ".join(map(str, cmd))))
		with subprocess.Popen(cmd, stdout=subprocess.PIPE) as ffmpeg:
				fd = ffmpeg.stdout.fileno()
				while ffmpeg.poll() is None:
					r, w, e = select.select([fd], [], [])
					if fd in r:
						yield os.read(fd, bs)
						

	def GenerateAsStreamAndSave(self, src_path, video_path):
		try:
			cmd = self.GetCmd(src_path)
			stream = self.GenerateAsStream(src_path, cmd)
			with open(video_path, "wb") as fs_file:
				for data in stream:
					yield data
					fs_file.write(data)

		except Exception as ex:
			log.exception(f"Cannot proccess video: {cmd}")
			try:
				os.remove(video_path)
			except Exception as ex:
				log.exception(f"Cannot remove bronken video {video_path}")


def GetVideoMeta(path):
	data = ffprobe_get_format(path)

	if not data or 'format' not in data:
		raise ValueError(f"Invalid file {path}")

	response = {
		'duration': 0
	}

	if 'duration' in data['format']:
		response['duration'] = max(response['duration'], float(data['format'].get('start_time', 0)) + float(data['format']['duration']))

	for stream in data.get('streams') or []:
		if 'duration' in stream:
			response['duration'] = max(response['duration'], float(stream.get('start_time', 0)) + float(stream['duration']))
		
		if stream.get('codec_type') == "audio":
			response['audio'] = {i: stream.get(i) for i in ('codec_name', 'codec_long_name', 'profile', 'sample_rate', 'channels', 'channel_layout', 'bit_rate', 'nb_frames')}
		elif stream.get('codec_type') == "video":
			response['video'] = {i: stream.get(i) for i in ('codec_name', 'codec_long_name', 'profile', 'width', 'height', 'sample_aspect_ratio', 'display_aspect_ratio', 'avg_frame_rate', 'duration_ts', 'bit_rate', 'nb_frames')}

	# {
	#  'duration': 10.05424,
	#  'video': {
	#     'codec_name': 'h264',
	#     'codec_long_name': 'H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10', 'profile': 'Main', 'width': 1280, 'height': 720,
	#     'sample_aspect_ratio': '1:1', 'display_aspect_ratio': '16:9', 'avg_frame_rate': '30000/1001', 'duration_ts': 903903, 'bit_rate': '2200785', 'nb_frames': '301'},
	#  'audio': {'codec_name': 'aac', 'codec_long_name': 'AAC (Advanced Audio Coding)', 'profile': 'LC', 'sample_rate': '44100', 'channels': 2,
	#     'channel_layout': 'stereo', 'bit_rate': '125587', 'nb_frames': '433'
	#   }
	# }
	return response


def ExtractFrame(path, output, at=0.0, quality=1):

	command = [
		"ffmpeg",
		"-y",
	    #"-loglevel", "quiet",
	    #"-print_format", "json",
		'-ss', str(float(at)),
		'-i', path,
		'-qscale:v', str(quality),
		'-frames:v', '1',
		output
	]

	pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	out, err = pipe.communicate()
	if err:
		log.error("Cannot extract frame from file %s: %s", path, err.decode("utf8"))
	if out:
		log.info("File extracted: %s", out.decode("utf8"))

	return pipe.returncode == 0


def ffprobe_get_format(path):

    command = [
		"ffprobe",
	    "-loglevel",  "quiet",
	    "-print_format", "json",
	    "-show_format",
	    "-show_streams",
	    path
	]

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = pipe.communicate()
    return json.loads(out)
