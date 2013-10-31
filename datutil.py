
import struct
import sys
from itertools import chain
from collections import namedtuple
from PIL import Image as PILImage

def readStr(file):
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
	pass

class SpritePackage:
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
	def __init__(self, imageId, step, delay):
		self.imageId = imageId
		self.step = step
		self.delay = delay
	
	def __str__(self):
		return "(Image: {0}, Step: {1}, Delay: {2})".format(self.imageId, self.step, self.delay)

class Animation():
	
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

def cmd_list(args):
	package = SpritePackage(file=args.file)
	print("Package:")
	print("\tVersion:", package.version)
	print("\tTexture Size:", package.textureSize)
	print("\tTexture Format:", package.textureFormat)
	for tx in package.textures:
		print("Texture:")
		print("\tID:", tx.id)
		print("\tImage:", tx.contents.mode, tx.contents.size)
	for name, img in package.images.items():
		print("Image:", img.name)
		print("\tID:", img.id)
		print("\tOffset:", img.offset)
		print("\tClip:", img.clipped)
		print("\tTexture:", img.textureNum)
		print("\tRect:", img.rect)
		print("\tOriginal Size:", img.originalSize)
	for name, bundle in package.bundles.items():
		print("Bundle:")
		print("\tName:", bundle.name)
		print("\tTexture:", bundle.textureNum)
	for name, anim in package.anims.items():
		print("Anim:", anim.name)

def cmd_showtex(args):
	with args.file:
		package = SpritePackage(file=args.file)
	if args.texid < 0 or args.texid >= len(package.textures):
		print("Bad texture id", file=sys.stderr)
		sys.exit(1)
	
	package.textures[args.texid].contents.show()

def cmd_extracttex(args):
	with args.file:
		package = SpritePackage(file=args.file)
	if args.texid < 0 or args.texid >= len(package.textures):
		print("Bad texture id", file=sys.stderr)
		sys.exit(1)
	
	package.textures[args.texid].contents.save(args.out)

def cmd_showanim(args):
	with args.file:
		package = SpritePackage(file=args.file)
	if args.anim not in package.anims:
		print("Bad anim:", args.anim, file=sys.stderr)
		sys.exit(1)
	
	anim = package.anims[args.anim]
	
	print("Anim:", anim.name)
	for i, frame in enumerate(anim.keyframes):
		print("\t", i, ": ", str(frame), sep="")

def cmd_sspack(args):	
	import re
	linere = re.compile(r"^([^\s]+)\s*=\s*(\d+)\s*(\d+)\s*(\d+)\s*(\d+)\s*$")
	
	package = SpritePackage()
	
	pilimg = PILImage.open(args.txfile)
	
	if pilimg.size[0] != pilimg.size[1] or ((pilimg.size[0] & (pilimg.size[0]-1)) != 0):
		print("Image must be square with powers of two dimensions", file=sys.stderr)
		sys.exit(1)
	
	package.textureSize = pilimg.size[0]
	
	tex = Texture(0)
	tex.contents = pilimg
	
	if pilimg.mode == "RGB":
		package.textureFormat = TEXTURE_FORMAT_RGB
	elif pilimg.mode == "RGBA":
		package.textureFormat = TEXTURE_FORMAT_RGBA
	elif pilimg.mode == "L":
		package.textureFormat = TEXTURE_FORMAT_A
	else:
		print("Incompatible image mode: "+img.mode, file=sys.stderr)
		sys.exit(1)
	
	package.textures.append(tex)
	
	with args.listfile:
		for i, line in enumerate(args.listfile):
			if line.strip() == "":
				continue
			
			match = linere.match(line)
			if not match:
				print("Bad input line: '{0}'".format(line), file=sys.stderr)
				sys.exit(1)
			
			name, x, y, w, h = match.groups()
			x, y, w, h = int(x), int(y), int(w), int(h)
			
			img = Image()
			img.name = name
			img.id = i
			img.rect = (x,y,w,h)
			img.originalSize = (w,h)
			package.images[img.name] = img
			
			anim = Animation()
			anim.name = name
			anim.keyframes.append(Keyframe(img.id, 1, -1))
			package.anims[anim.name] = anim
	
	with args.out:
		package.write(args.out)	

if __name__ == "__main__":
	import argparse
	
	# Argument parsing
	parser = argparse.ArgumentParser(description="Utilities for working with Cobalt sprite packages.")
	subparsers = parser.add_subparsers(dest="command")
	
	# Command: list
	parser_list = subparsers.add_parser("list", help="Lists the contents of a sprite package.")
	parser_list.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
	
	# Command: showtex
	parser_showtex = subparsers.add_parser("showtex", help="Previews a texture.")
	parser_showtex.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
	parser_showtex.add_argument("texid", type=int, help="Texture ID to show.")
	
	# Command: extracttex
	parser_extracttex = subparsers.add_parser("extracttex", help="Exports a texture as an image file.")
	parser_extracttex.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
	parser_extracttex.add_argument("texid", type=int, help="Texture ID to export.")
	parser_extracttex.add_argument("out", help="Output file. Image type detected from the extension.")
	
	# Command: showanim
	parser_showanim = subparsers.add_parser("showanim", help="Shows the contents of an animation.")
	parser_showanim.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
	parser_showanim.add_argument("anim", help="Animation name")
	
	# Command: sspack
	parser_sspack = subparsers.add_parser("sspack", help="Creates a simple sprite package from a Spritesheet Packer file.")
	parser_sspack.add_argument("txfile", help="Input texture file.")
	parser_sspack.add_argument("listfile", type=argparse.FileType("r"), help="Input list file. Contains lines in the format 'name = x y w h'.")
	parser_sspack.add_argument("out", type=argparse.FileType("wb"), help="Sprite package file.")	
	
	# Go to commands
	args = parser.parse_args()
	
	if not args.command:
		parser.error("Please specify a command")
	elif args.command == "list":
		cmd_list(args)
	elif args.command == "showtex":
		cmd_showtex(args)
	elif args.command == "extracttex":
		cmd_extracttex(args)
	elif args.command == "showanim":
		cmd_showanim(args)
	elif args.command == "sspack":
		cmd_sspack(args)
	else:
		raise RuntimeError("Unhandled command: "+args.command)
