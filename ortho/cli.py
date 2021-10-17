#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Command-line helpers.
"""

import os
import sys
import re
import ast
import functools
from .reexec import interact
from .utils import is_empty_function

def cli_args_to_kwargs(*args,separator='='):
	"""
	Parse a list arguments from click into key-value pairs.
	Send args from @click.argument('args',nargs=-1) to get kwargs back.

	This is one method for receiving unstructured key-value pairs from
	the command line. It is otherwise difficult to do this in click in 
	a way that respects the typicall `--key value` syntax onthe command line.
	One option is [here](https://stackoverflow.com/a/48394004/3313859), but
	this method still produces args and not kwargs, which would require more
	parsing anyway. Using this option is relatively elegant.
	"""
	kwargs = {}
	for arg in args:
		key,val = re.match(f'^(.*?){separator}(.*?)$',arg).groups()
		val = ast.literal_eval(val)
		if key in kwargs: 
			raise KeyError(f'key collision: {key}')
		kwargs[key] = val
	return kwargs

def click_args_to_kwargs(args_kw='args'):
	def outer(func):
		def inner(*args,**kwargs):
			if args_kw in kwargs:
				args_out = kwargs.pop(args_kw)
				kwargs_out = cli_args_to_kwargs(args_out)
				if args:
					return func(**kwargs_out,**kwargs)
				else:
					return func(*args,**kwargs_out,**kwargs)
			elif not args:
				print('no *args in a function wrapped with `click_args_to_kwargs`')
			else:
				kwargs_out = cli_args_to_kwargs(args)
				return func(**kwargs_out,**kwargs)
		inner.__name__ = func.__name__
		inner.__doc__ = func.__doc__
		return inner
	return outer

def redirect(func_real):
	"""
	Decorator used to separate the CLI interface from the elements.
	This decorator replaces the decorated function with the argument (which should be a function) so that we
	can separate the click CLI interface from the function itself. This facilitates modular code.	
	"""
	# make sure the dummy function is a dummy
	def outer(func):
		if not is_empty_function(func):
			raise Exception('when using redirect your function must be empty')
		def inner(*args,**kwargs):
			# dev: check that func_real is a function?
			return func_real(*args,**kwargs)
		# crucially we use the name of the dummy function as the exposed name
		#   which means that you can rename the function where it is decorated
		#   with other click functions
		inner.__name__ = func.__name__
		inner.__doc__ = func_real.__doc__
		return inner
	return outer

def identity(func):
	"""The identity decorator."""
	# this method provides a 
	def inner(*args,**kwargs):
		return func(*args,**kwargs)
	inner.__name__ = func.__name__
	inner.__doc__ = func.__doc__
	return inner
	
def scripter(fn,spot=None):
	"""
	Decorator which calls a script interactively and discards the function.
	"""
	# the calling module should send along the file so we know where to look
	#   for the script which we will be calling interactively
	# dev: automatically detect the file from the originating module scope
	def outer(func):
		def inner(**kwargs):
			# get the parent module
			mod_base = func.__module__.split('.')[0]
			# get the parent module path
			mod_base_dn = os.path.dirname(sys.modules[mod_base].__file__)
			script_fn = os.path.join(mod_base_dn,fn)
			interact(script_fn,onward=kwargs)
		inner.__name__ = func.__name__
		inner.__doc__ = func.__doc__
		return inner
	return outer
