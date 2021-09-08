#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Orthopraxy runpy tools.

Usage examples: 

python -m ortho interact -i <script_dev.py>
"""

import os
import argparse
import shutil

from .reexec import interact

def interact_router(script):
	"""Route module runpy requests for interactive mode to ortho."""
	return interact(script=script)

def boilerplate_cli():
	"""Report a basic boilerplate CLI with instructions."""
	with open(os.path.join(
		os.path.dirname(__file__),'cli_example.txt')) as fp:
		text = fp.read()
		print(text)

cli_toc = {
	'interact':{
		'func':interact_router,
		'parser':dict(
			name='interact',
			help=f'Develop a script interactively.'),
		'args':[
			(('-i',),dict(
				dest='script',
				help='Target script.',
				required=True),),]},
	'boilerplate_cli':{
		'func':boilerplate_cli,
		'parser':dict(
			name='boilerplate_cli',),},}

if __name__ == '__main__':

	parser_parent = argparse.ArgumentParser(
		epilog='Entry point for ortho tools.')
	subparsers = parser_parent.add_subparsers(
		dest='subparser_name',
		help='sub-command help')

	subparsers_toc = {}
	for name,detail in cli_toc.items():
		print(name)
		subparsers_toc[name] = subparsers.add_parser(
			**detail['parser'])
		for args,kwargs in detail.pop('args',[]):
			subparsers_toc[name].add_argument(*args,**kwargs)
	
	# parse arguments
	args = parser_parent.parse_args()

	if not args.subparser_name:
		parser_parent.print_help()
		
	# call the subcommand function
	else:
		name = args.__dict__.pop('subparser_name')
		# pass the namespace sans subparser name to the function
		cli_toc[name]['func'](**args.__dict__)