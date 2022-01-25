#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import re
import ast

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
	arglist = []
	arglist.extend(args)
	while arglist:
		arg = arglist.pop()
		if isinstance(arg,tuple):
			arglist.extend(arg)
		else:
			key,val = re.match(f'^(.*?){separator}(.*?)$',arg).groups()
			val = ast.literal_eval(val)
			if key in kwargs: 
				raise KeyError(f'key collision: {key}')
			kwargs[key] = val
	return kwargs

def click_args_to_kwargs(args_kw='args'):
	# dev: needs docs
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
				print((args,kwargs))
				raise Exception('no *args in a function wrapped with `click_args_to_kwargs`. to fix this, '
					'send args_kw to `click_args_to_kwargs` to name the typical *args variable or use the '
					'current value (%s).'%args_kw)
			else:
				kwargs_out = cli_args_to_kwargs(args)
				return func(**kwargs_out,**kwargs)
		inner.__name__ = func.__name__
		inner.__doc__ = func.__doc__
		return inner
	return outer
