#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import sys
import re

# adjucate string types between versions. use `type(a) in str_types` for light
#   scripting. this is a legacy solution consistent with basestring or
#   six.string_types we skip six.string_types because it has the same role as
#   the following recommended string checking is via
#   isinstance(u'string',basestring). this is only necessary for python 2
#   compatibility which is declining in importance
if sys.version_info < (3,0):
	str_types = (str,unicode) # noqa: F821 # pylint: disable=undefined-variable
else:
	str_types = (str,)
basestring = string_types = str_types
str_types_list = list(str_types)

def stylized_print(override=False):
	"""
	Prepare a special override print function.
	This decorator stylizes print statements so that printing a tuple that
	begins with words like `status` will cause print to prepend `[STATUS]` to
	each line. This makes the output somewhat more readable but otherwise does
	not affect printing. We use builtins to distribute the function. Any python
	2 code which imports `print_function` from `__future__` gets the stylized
	print function. Any python 3 code which uses print will print this
	correctly. The elif which uses a regex means that the overloaded print can
	turn e.g. print('debug something bad happened') into "[DEBUG] something bad
	happened" in stdout.
	"""
	# python 2/3 builtins
	try: import __builtin__ as builtins # type: ignore
	except ImportError: import builtins
	# use custom print function everywhere
	if builtins.__dict__['print'].__name__ != 'print_stylized':
		# every script must import print_function from __future__
		#   or else you get a syntax error
		# hold the standard print
		_print = print
		key_leads = ['status','warning','error','note','usage',
			'exception','except','question','run','tail','watch',
			'bash','debug']
		key_leads_regex = re.compile(
			r'^(?:(%s)(?:\s|:\s)?)(.+)$'%'|'.join(key_leads))

		def print_stylized(*args,**kwargs):
			"""Custom print function."""
			if (len(args)>0 and
				isinstance(args[0],str_types) and args[0] in key_leads):
				return _print('[%s]'%args[0].upper(),*args[1:])
			# regex here adds very little time and allows more natural print
			#   statements to be capitalized
			elif len(args)==1 and isinstance(args[0],str_types):
				match = key_leads_regex.match(args[0])
				if match: return _print(
					'[%s]'%match.group(1).upper(),match.group(2),**kwargs)
				else: return _print(*args,**kwargs)
			else: return _print(*args,**kwargs)

		# export custom print function before other imports
		# this code ensures that in python 3 we overload print
		#   while any python 2 code that wishes to use overloaded print
		#   must of course from __future__ import print_function
		builtins.print = print_stylized
