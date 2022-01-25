#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import re
import os
from .bash import bash

def get_git_hash(path):
	"""
	Collect the git hash.
	"""
	result = bash(f'git -C {path} rev-parse HEAD',quiet=True)
	return result['stdout'].strip()

def code_current(source,path,strict=True):
	"""Check or clone the source code."""
	path_abs = os.path.abspath(path)
	# if the path is absent we clone
	if not os.path.isdir(path):
		bash(f'git clone {source} {path}',announce=True)	
	# make sure the code is up to date otherwise
	else:
		# via: https://stackoverflow.com/a/52307619/3313859
		# via: https://stackoverflow.com/a/43115337/3313859
		result = bash(f'git -C {path} remote show origin',
			permit_fail=True,quiet=True)
		if re.findall('local out of date',result['stdout']):
			if not strict:
				print('warning: your code (%s) is out of date'%path)
			else:
				raise Exception('your local code (%s) is out of date!'%path)
	return get_git_hash(path=path)
