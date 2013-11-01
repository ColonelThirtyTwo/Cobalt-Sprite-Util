
import struct
from PIL import Image as PILImage

def readStr(file):
	"""
	Reads a null terminated ASCII string from a binary file.
	"""
	l = []
	c = file.read(1)
	while c != b'\x00':
		l.append(c[0])
		c = file.read(1)
	return bytes(l).decode("ascii")

TEXTURE_FORMAT_RGB = 0
TEXTURE_FORMAT_RGBA = 1
TEXTURE_FORMAT_A = 2
TEXTURE_FORMAT_SPECIAL_AI = 3

BASE_ID_IMAGES = 0
BASE_ID_BUNDLES = 100000

class BadFileFormatError(Exception):
	"""
	Exception thrown when the input file is not a valid sprite package.
	"""
	pass

class SpritePackage:
	"""
	Represents a sprite package in memory, and provides facilities for
	reading/writing them.
	
	A sprite package contains
	* textures, which are spri,
	* images, which are sections of a texture corresponding to individual sprites,
	* image bundles, which are collections of images, and
	* animations
	"""
	def __init__(self, file=None):
		self.version = 3
		self.textureSize = 0
		self.textureFormat = 0
		
		self.textures = []
		self.images = {}
		self.bundles = {}
		self.anims = {}
		
		if file is not None:
			self.version       = struct.unpack("<I", file.read(4))[0]
			if self.version != 3:
				raise BadFileFormatError("Unsupported version: "+self.version)
			
			self.textureSize   = struct.unpack("<I", file.read(4))[0]
			self.textureFormat = struct.unpack("<I", file.read(4))[0]
			
			numTextures = struct.unpack("<I", file.read(4))[0]
			numImages   = struct.unpack("<I", file.read(4))[0]
			numBundles  = struct.unpack("<I", file.read(4))[0]
			numAnims    = struct.unpack("<I", file.read(4))[0]
			
			for i in range(numTextures):
				self.textures.append(Texture(id=i, file=file, size=self.textureSize, format=self.textureFormat))
			for i in range(numImages):
				img = Image(file=file)
				self.images[img.name] = img
			for i in range(numBundles):
				bndl = ImageBundle(file=file)
				self.bundles[bndl.name] = bndl
			for i in range(numAnims):
				anim = Animation(file=file)
				self.anims[anim.name] = anim
	
	def write(self, file):
		file.write(struct.pack("<I", self.version))
		file.write(struct.pack("<I", self.textureSize))
		file.write(struct.pack("<I", self.textureFormat))
		
		file.write(struct.pack("<I", len(self.textures)))
		file.write(struct.pack("<I", len(self.images)))
		file.write(struct.pack("<I", len(self.bundles)))
		file.write(struct.pack("<I", len(self.anims)))
		
		
		for i in self.textures:
			i.write(file)
		for i in sorted(self.images.values(), key=lambda x: x.id):
			i.write(file)
		for i in sorted(self.bundles.values(), key=lambda x: x.id):
			i.write(file)
		for i in sorted(self.anims.values(), key=lambda x: x.name):
			i.write(file)

class Texture:
	"""
	Spritesheet image.
	
	Textures must be square and have powers-of-two dimensions.
	Every texture in a sprite package must have the same size and format.
	
	Textures can be RGB, RGBA, A, or "Special AI" (not supported yet)
	"""
	def __init__(self, id, file=None, size=None, format=None):
		self.id = id
		self.isSpecialAI = False
		self.contents = None
		
		if file is not None:
			if size is None:
				raise ValueError("size must not be none")
			if format is None:
				raise ValueError("format must not be none")
			
			# Read format and create the image
			#format = struct.unpack("<I", file.read(1))[0]
			if format == TEXTURE_FORMAT_RGB:
				mode = "RGB"
				channels = 3
				
			elif format == TEXTURE_FORMAT_RGBA:
				mode = "RGBA"
				channels = 4
				
			elif format == TEXTURE_FORMAT_A:
				mode = "L"
				channels = 1
				
			else:
				raise BadFileFormatError("unknown texture format: "+format)
			
			# Read the image contents
			texdata = bytearray(size*size*channels)
			for c in range(channels):
				for i in range(size*size):
					texdata[i*channels+c] = file.read(1)[0]
			texdata = bytes(texdata)
			self.contents = PILImage.frombytes(mode, (size,size), texdata)
			
	def write(self, file):	
		for channel in self.contents.split():
			for px in channel.getdata():
				file.write(struct.pack("B", px))

class ImageBase:
	"""
	Base class for images. Do not use this directly!
	"""
	def __init__(self, file=None):
		self.name = ""
		self.id = 0
		self.offset = (0,0)
		self.clipped = (0,0)
		
		if file is not None:
			self.name = readStr(file)
			self.id = struct.unpack("<I", file.read(4))[0]
			self.offset = (
				struct.unpack("<i", file.read(4))[0],
				struct.unpack("<i", file.read(4))[0]
			)
			self.clipped = (
				struct.unpack("<i", file.read(4))[0],
				struct.unpack("<i", file.read(4))[0]
			)
		
	def write(self, file):
		file.write(self.name.encode("ascii"))
		file.write(b"\x00")
		file.write(struct.pack("<I", self.id))
		file.write(struct.pack("<i", self.offset[0]))
		file.write(struct.pack("<i", self.offset[1]))
		file.write(struct.pack("<I", self.clipped[0]))
		file.write(struct.pack("<I", self.clipped[1]))

class Image(ImageBase):
	"""
	Defines a single sprite in a textures.
	"""
	def __init__(self, file=None):
		super(Image, self).__init__(file=file)
		self.textureNum = 0
		self.rect = (0,0,1,1) # x,y,w,h
		self.originalSize = (0,0)
		
		if file is not None:
			self.textureNum = struct.unpack("<I", file.read(4))[0]
			self.rect = (
				struct.unpack("<I", file.read(4))[0],
				struct.unpack("<I", file.read(4))[0],
				struct.unpack("<I", file.read(4))[0],
				struct.unpack("<I", file.read(4))[0]
			)
			self.originalSize = (
				struct.unpack("<I", file.read(4))[0],
				struct.unpack("<I", file.read(4))[0]
			)
	
	def write(self, file):
		super(Image, self).write(file)
		file.write(struct.pack("<I", self.textureNum))
		for n in self.rect:
			file.write(struct.pack("<I", n))
		for n in self.originalSize:
			file.write(struct.pack("<I", n))

class ImageBundle(ImageBase):
	"""
	Defines a collection of images.
	This doesn't seem to be used much, and has not been thoroughly tested.
	"""
	def __init__(self, file=None):
		super(ImageBundle, self).__init__(file=file)
		self.images = []
		self.widthCount = 1
		
		if file is not None:
			self.widthCount = struct.unpack("<I", file.read(4))[0]
			numImages = struct.unpack("<I", file.read(4))[0]
			for i in range(numImages):
				self.images.append(Image(file=file))
	
	def write(self, file):
		super(Image, self).write(file)
		file.write(struct.pack("<I", self.width))
		file.write(struct.pack("<I", len(self.images)))
		for i in self.images:
			i.write(file)

class Keyframe:
	"""
	A single frame of animation.
	"""
	def __init__(self, imageId, step, delay):
		self.imageId = imageId
		self.step = step
		self.delay = delay
	
	def __str__(self):
		return "(Image: {0}, Step: {1}, Delay: {2})".format(self.imageId, self.step, self.delay)

class Animation:
	"""
	Defines an animation.
	
	Most sprites have a single, static animation with one frame.
	"""
	def __init__(self, file=None):
		self.name = ""
		self.keyframes = []
		
		if file is not None:
			self.name = readStr(file)
			numKeyframes = struct.unpack("<i", file.read(4))[0]
			for i in range(numKeyframes):
				imageId = struct.unpack("<i", file.read(4))[0]
				self.keyframes.append(Keyframe(imageId, None, None))
			for i in range(numKeyframes):
				step = struct.unpack("<i", file.read(4))[0]
				self.keyframes[i].step = step
			for i in range(numKeyframes):
				delay = struct.unpack("<i", file.read(4))[0]
				self.keyframes[i].delay = delay
	
	def write(self, file):
		file.write(self.name.encode("ascii"))
		file.write(b"\x00")
		file.write(struct.pack("<i", len(self.keyframes)))
		for i in self.keyframes:
			file.write(struct.pack("<i", i.imageId))
		for i in self.keyframes:
			file.write(struct.pack("<i", i.step))
		for i in self.keyframes:
			file.write(struct.pack("<i", i.delay))
