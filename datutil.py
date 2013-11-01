
import sys
from spritepackage import *

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

# ########################################################################

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
