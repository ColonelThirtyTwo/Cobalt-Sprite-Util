
import sys
from spritepackage import *

class BaseCommand:
	name = "__REPLACEME__"
	help = ""
	
	def addParser(self, subparsers):
		return subparsers.add_parser(self.name, help=self.help)
	
	def execute(self, args):
		raise NotImplementedError("Implement BaseCommand.execute!")

commands = {}
def register(cls):
	cmd = cls()
	commands[cmd.name] = cmd
	return cls

def exitError(*args):
	print(*args, file=sys.stderr)
	sys.exit(1)

# #################################################################

@register
class ListCommand(BaseCommand):
	name = "list"
	help = "Lists the contents of a sprite package."
	
	def addParser(self, subparsers):
		parser = super().addParser(subparsers)
		parser.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
	
	def execute(self, args):
		with args.file:
			package = SpritePackage.read(args.file)
		
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

@register
class ShowTexCommand(BaseCommand):
	name = "showtex"
	help = "Previews a texture."
	
	def addParser(self, subparsers):
		parser = super().addParser(subparsers)
		parser.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
		parser.add_argument("texid", type=int, help="Texture ID to show.")
	
	def execute(self, args):
		with args.file:
			package = SpritePackage.read(args.file)
		
		if args.texid < 0 or args.texid >= len(package.textures):
			exitError("Bad texture ID:", str(args.texid), "/", len(package.textures))
		
		package.textures[args.texid].contents.show()

@register
class ExtractTexCommand(BaseCommand):
	name = "extracttex"
	help = "Extracts a texture as an image file."
	
	def addParser(self, subparsers):
		parser = super().addParser(subparsers)
		parser.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
		parser.add_argument("texid", type=int, help="Texture ID to export.")
		parser.add_argument("out", help="Output file. Image type detected from the extension.")
	
	def execute(self, args):
		with args.file:
			package = SpritePackage.read(args.file)
		if args.texid < 0 or args.texid >= len(package.textures):
			exitError("Bad texture ID:", str(args.texid), "/", len(package.textures))
		
		package.textures[args.texid].contents.save(args.out)

@register
class ShowAnimCommand(BaseCommand):
	name = "showanim"
	help = "Shows frames in an animation."
	
	def addParser(self, subparsers):
		parser = super().addParser(subparsers)
		parser.add_argument("file", type=argparse.FileType("rb"), help="Sprite package file.")
		parser.add_argument("anim", help="Animation name.")
	
	def execute(self, args):
		with args.file:
			package = SpritePackage.read(args.file)
		if args.anim not in package.anims:
			exitError("Bad anim:", args.anim)
		
		anim = package.anims[args.anim]
		
		print("Anim:", anim.name)
		for i, frame in enumerate(anim.keyframes):
			print("\t", i, ": ", str(frame), sep="")

@register
class SSPackCommand(BaseCommand):
	name = "sspack"
	help = "Creates a sprite package from the output of Sprite Sheet Packer"
	
	def addParser(self, subparsers):
		parser = super().addParser(subparsers)
		parser.add_argument("txfile", help="Input texture file.")
		parser.add_argument("listfile", type=argparse.FileType("r"), help="Input list file. Contains lines in the format 'name = x y w h'.")
		parser.add_argument("out", type=argparse.FileType("wb"), help="Sprite package file.")
	
	def execute(self, args):
		import re
		linere = re.compile(r"^([^\s]+)\s*=\s*(\d+)\s*(\d+)\s*(\d+)\s*(\d+)\s*$")
		
		package = SpritePackage()
		
		pilimg = PILImage.open(args.txfile)
		
		if pilimg.size[0] != pilimg.size[1] or ((pilimg.size[0] & (pilimg.size[0]-1)) != 0):
			exitError("Image must be square with powers of two dimensions")
		
		package.textureSize = pilimg.size[0]
		
		tex = Texture(0, pilimg)
		
		if pilimg.mode == "RGB":
			package.textureFormat = TEXTURE_FORMAT_RGB
		elif pilimg.mode == "RGBA":
			package.textureFormat = TEXTURE_FORMAT_RGBA
		elif pilimg.mode == "L":
			package.textureFormat = TEXTURE_FORMAT_A
		else:
			exitError("Incompatible image mode:", img.mode)
		
		package.textures.append(tex)
		
		with args.listfile:
			for i, line in enumerate(args.listfile):
				if line.strip() == "":
					continue
				
				match = linere.match(line)
				if not match:
					exitError("Bad input line: '{0}'".format(line))
				
				name, x, y, w, h = match.groups()
				x, y, w, h = int(x), int(y), int(w), int(h)
				
				img = Image(i, name, 0, (x,y,w,h))
				package.images[img.name] = img
				
				anim = Animation(name)
				anim.keyframes.append(Keyframe(img.id, 1, -1))
				package.anims[anim.name] = anim
		
		with args.out:
			package.write(args.out)	

# ########################################################################

if __name__ == "__main__":
	import argparse
	
	# Argument parsing
	parser = argparse.ArgumentParser(description="Utilities for working with Cobalt sprite packages.")
	subparsers = parser.add_subparsers(dest="command")
	
	for cmd in commands.values():
		cmd.addParser(subparsers)
	
	# Go to commands
	args = parser.parse_args()
	
	if not args.command:
		parser.error("Please specify a command")
	
	commands[args.command].execute(args)
