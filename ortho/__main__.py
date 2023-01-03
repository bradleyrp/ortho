#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Orthopraxy runpy tools.

Usage examples: 

python -m ortho interact -d -i <script_dev.py>
"""

import os
import argparse
import shutil

from .reexec import interact,debugger

def subcommander_argparse(cli_index):
	"""
	This generic function implements a subcommand argparser from a dict.
	"""
	parser_parent = argparse.ArgumentParser(
		epilog='Entry point for ortho tools.')
	subparsers = parser_parent.add_subparsers(
		dest='subparser_name',
		help='sub-command help')
	subparsers_toc = {}
	for name,detail in cli_index.items():
		subparsers_toc[name] = subparsers.add_parser(
			**detail['parser'])
		for args,kwargs in detail.pop('args',[]):
			subparsers_toc[name].add_argument(*args,**kwargs)
	# parse known arguments
	args,_ = parser_parent.parse_known_args()
	# we only parse known arguments in case you use argparser in the development
	#   script. you would also need to use `parse_known_args` there. functions
	#   which are later added to a package should be given their own parsers.
	#   note that the author prefers click. see an example from the command:
	#   `python -m ortho boilerplate_cli`
	if not args.subparser_name:
		parser_parent.print_help()
	# call the subcommand function
	else:
		name = args.__dict__.pop('subparser_name')
		# pass the namespace sans subparser name to the function
		cli_index[name]['func'](**args.__dict__)

### section (missing records, previously the section included an alert)

import sys
import inspect

def introspect_function(func,**kwargs):
	"""
	Get arguments and kwargs expected by a function.
	"""
	# the self object remains in the argument list in old python
	selfless = lambda x: [i for i in x if i!='self']
	message = kwargs.pop('message',(
		'function introspection received a string instead of a function '
		'indicating that we have gleaned the function without importing it. '
		'this indicates an error which requires careful debugging.'))
	#! message is unused
	check_varargs = kwargs.pop('check_varargs',False)
	if kwargs: raise Exception('kwargs: %s'%kwargs)
	# getargspec will be deprecated by Python 3.6
	if sys.version_info<(3,3): 
		if isinstance(func,str_types): raise Exception(messsage)
		args,varargs,varkw,defaults = inspect.getargspec(func)
		# python 2 includes self in this list
		if defaults: 
			std,var = args[:-len(defaults)],args[-len(defaults):]
			packed = dict(args=tuple(selfless(std)),
				kwargs=dict(zip(var,defaults)))
		else: 
			packed = dict(kwargs={},args=tuple(selfless(args)))
		if check_varargs and varargs: packed['*'] = varargs
		if varkw: packed['**'] = varkw
		return packed
	else:
		#! might need to validate this section for python 3 properly
		sig = inspect.signature(func) # pylint: disable=no-member
		args_collect = tuple([key for key,val in sig.parameters.items() 
			if val.default==inspect._empty])
		# decorators add self to the argument list somehow so we filter
		packed = {'args':selfless(args_collect)}
		keywords = [(key,val.default) for key,val in sig.parameters.items() 
			if val.default!=inspect._empty]
		packed['kwargs'] = dict(keywords)
		#! probably only one double star is allowed anyway so list is confusing
		double_star = [i for i in sig.parameters 
			if str(sig.parameters[i]).startswith('**')]
		if len(double_star)>1:
			raise Exception('unexpected number of double stars: %s'%
				str(double_star))
		if double_star: packed['**'] = double_star[0]
		if check_varargs:
			varargs = inspect.getfullargspec(func).varargs
			if varargs: packed['*'] = varargs
		return packed

class Everything:
	_router = {}
	def __init__(self,*args,**kwargs):
		self.args = args
		self.kwargs = kwargs
	def _call(self):
		for key,val in self._router.items():
			print('checking',key,val)
	@property
	def call(self):
		return self._call()

def register(cls):
	def outer(func):
		def inner(*args,**kwargs):
			print(cls.kwargs[func.__name__])
			return 111
		setattr(Everything,func.__name__,func)
		intro = introspect_function(func)
		cls._router[func.__name__] = intro
		return inner
	return outer

@register(Everything)
def method_1(a,b):
	print('i am ab')

@register(Everything)
def method_2(a,b,c):
	print('i am ab')

def docker_router(*args,**kwargs):
	print(123)
	this = Everything(a=1,b=2).call

### section

# exposed functions for the ooo utility
cli_index_ooo = {
	'dock':{
		'func':docker_router,
		'parser':dict(
			name='dock',
			help=f'Execute a container.'),
		'args':[
			(('-i',),dict(
				dest='code',
				help='Target code.',
				required=True)),]},}

def ooo():
	"""Expose the docker tools to the `ort` command."""
	subcommander_argparse(cli_index=cli_index_ooo)

def interact_router(script,debug=False):
	"""Route module runpy requests for interactive mode to ortho."""
	try: 
		this = interact(script=script)
		return this
	except: 
		if debug: debugger()
		else: raise

def boilerplate_cli():
	"""Report a basic boilerplate CLI with instructions."""
	with open(os.path.join(
		os.path.dirname(__file__),'cli_example.txt')) as fp:
		text = fp.read()
		print(text)

# index of exposed functions to the runpy interface: `python -m ortho`
cli_index_runpy = {
	'interact':{
		'func':interact_router,
		'parser':dict(
			name='interact',
			help=f'Develop a script interactively.'),
		'args':[
			(('-i',),dict(
				dest='script',
				help='Target script.',
				required=True)),
			(('-d','--debug',),dict(
				dest='debug',
				help='Enable on-site debugging.',
				action='store_true',
				required=False)),]},
	'boilerplate_cli':{
		'func':boilerplate_cli,
		'parser':dict(
			name='boilerplate_cli',),},}

if __name__ == '__main__': 
	subcommander_argparse(cli_index=cli_index_runpy)
