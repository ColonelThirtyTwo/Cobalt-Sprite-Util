
import struct
from itertools import chain
from collections import namedtuple
from PIL import Image

def readStr(file):
	l = []
	c = file.read(1)
	while c != b'\x00':
		l.append(c)
		c = file.read(1)
	return str(bytes(l), "utf-8")

TEXTURE_FORMAT_RGB = 0
TEXTURE_FORMAT_RGBA = 1
TEXTURE_FORMAT_A = 2
TEXTURE_FORMAT_SPECIAL_AI = 3

BASE_ID_IMAGES = 0
BASE_ID_BUNDLES = 100000

class BadFileFormatError(Exception):
	pass

class SpritePackage:
	def __init__(self, file=None):
		self.version = 3
		self.textureSize = 0
		self.textureFormat = 0
		
		self.textures = []
		self.images = {}
		self.bundles = {}
		self.anims = []
		
		if file is not None:
			self.version       = struct.unpack("<I", file.read(4))
			if self.version != 3:
				raise BadFileFormatError("Unsupported version: "+self.version)
			
			self.textureSize   = struct.unpack("<I", file.read(4))
			self.textureFormat = struct.unpack("<I", file.read(4))
			
			numTextures = struct.unpack("<I", file.read(4))
			numImages   = struct.unpack("<I", file.read(4))
			numBundles  = struct.unpack("<I", file.read(4))
			numAnims    = struct.unpack("<I", file.read(4))
			
			for i in range(numTextures):
				self.textures.append(Texture(file=file, size=self.texutreSize, format=self.textureFormat))
			for i in range(numImages):
				img = Image(file=file)
				self.images[img.name] = img
			for i in range(numBundles):
				bndl = ImageBundle(file=file)
				self.bundles[bndl.name] = bndl
			for i in range(numAnims):
				self.anims.append(Animation(file=file))
	
	def write(file):
		file.write(struct.pack("<I", self.version))
		file.write(struct.pack("<I", self.textureSize))
		file.write(struct.pack("<I", self.textureFormat))
		
		file.write(struct.pack("<I", len(self.textures)))
		file.write(struct.pack("<I", len(self.images)))
		file.write(struct.pack("<I", len(self.bundles)))
		file.write(struct.pack("<I", len(self.anims)))
		
		for i in chain(self.textures, self.images, self.bundles, self.anims):
			i.write(file)

class Texture:
	def __init__(self, file=None, size=None, format=None):
		self.isSpecialAI = True
		self.width = 0
		self.height = 0
		self.contents = None
		
		if file is not None:
			if size is None:
				raise ValueError("size must not be none")
			if format is None:
				raise ValueError("format must not be none")
			
			# Read format and create the image
			#format = struct.unpack("<I", file.read(1))
			if format == TEXTURE_FORMAT_RGB:
				self.contents = Image.new("RGB", (size,size))
				channels = 3
				
			elif format == TEXTURE_FORMAT_RGBA:
				self.contents = Image.new("RGBA", (size,size))
				channels = 4
				
			elif format == TEXTURE_FORMAT_A:
				self.contents = Image.new("L", (size,size))
				channels = 1
				
			else:
				raise BadFileFormatError("unknown texture format: "+format)
			
			# Read the image contents, arrange them into pixel tuples, and copy it into the image
			texdata = bytearray(size*size*channels)
			for c in range(channels):
				for i in range(size*size):
					texdata[i*channels+c] = struct.unpack("B", file.read(1))
			self.contents.putdata(texdata)
	
	def write(file):	
		for channel in self.contents.split():
			for px in channel:
				file.write(struct.pack("B", px))

class ImageBase:
	def __init__(self, file=None):
		self.name = ""
		self.id = 0
		self.offset = (0,0)
		self.clipped = (0,0)
		
		if file is not None:
			self.name = readStr(file)
			self.id = struct.unpack("<I", file.read(4))
			self.offset = (
				struct.unpack("<I", file.read(4)),
				struct.unpack("<I", file.read(4))
			)
			self.clipped = (
				struct.unpack("<I", file.read(4)),
				struct.unpack("<I", file.read(4))
			)
		
	def write(file):
		file.write(self.name.encode("ascii"))
		file.write(b"\x00")
		file.write(struct.pack("<I", self.id))
		file.write(struct.pack("<I", self.offset[0]))
		file.write(struct.pack("<I", self.offset[1]))
		file.write(struct.pack("<I", self.clipped[0]))
		file.write(struct.pack("<I", self.clipped[1]))

class Image(ImageBase):
	def __init__(self, file=None):
		super(Image, self).__init__(self, file=file)
		self.textureNum = 0
		self.rect = (0,0,1,1) # x,y,w,h
		self.originalSize = (0,0)
		
		if file is not None:
			self.textureNum = struct.unpack("<I", file.read(4))
			self.rect = (
				struct.unpack("<I", file.read(4)),
				struct.unpack("<I", file.read(4)),
				struct.unpack("<I", file.read(4)),
				struct.unpack("<I", file.read(4))
			)
			self.originalSize = (
				struct.unpack("<I", file.read(4)),
				struct.unpack("<I", file.read(4))
			)
	
	def write(file):
		super(Image, self).write(file)
		file.write(struct.pack("<I", self.textureNum))
		for n in self.rect:
			file.write(struct.pack("<I", n))
		for n in self.originalSize:
			file.write(struct.pack("<I", n))

class ImageBundle(ImageBase):
	def __init__(self, file=None):
		super(ImageBundle, self).__init__(self)
		self.images = []
		self.widthCount = 1
		
		if file is not None:
			self.widthCount = struct.unpack("<I", file.read(4))
			numImages = struct.unpack("<I", file.read(4))
			for i in range(numImages):
				self.images.append(Image(file=file))
	
	def write(file):
		super(Image, self).write(file)
		file.write(struct.pack("<I", self.width))
		file.write(struct.pack("<I", len(self.images)))
		for i in self.images:
			i.write(file)

Keyframe = namedtuple("Keyframe", ("imageId", "step", "delay"))

class Animation():
	
	def __init__(self, file=None):
		self.name = ""
		self.keyframes = []
		#self.imageIds = []
		#self.steps = []
		#self.delays = []
		self.associatedTexture = -1
	
	def write(file):
		file.write(self.name.encode("ascii"))
		file.write(b"\x00")
		file.write(struct.pack("<I", len(self.keyframes)))
		for i in self.keyframes:
			file.write(struct.pack("<I", i.imageId))
		for i in self.keyframes:
			file.write(struct.pack("<I", i.step))
		for i in self.keyframes:
			file.write(struct.pack("<I", i.delay))


if __name__ == "__main__":
	import argparse
	
	
	
	pass
