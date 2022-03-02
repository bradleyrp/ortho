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

def code_current(source,path,branch=None,strict=True):
	"""Check or clone the source code."""
	path_abs = os.path.abspath(path)
	# if the path is absent we clone
	if not os.path.isdir(path):
		bash(f'git clone {source} {path}'+(
			f' -b {branch}' if branch else ''),announce=True)	
	# make sure the code is up to date otherwise
	else:
		result = bash(f'git -C {path} branch')
		stdout = result['stdout']
		branches = [re.match('(?P<active>\*)?\s+(?P<name>.*?)\s*$',i).groupdict() 
			for i in stdout.splitlines()]
		branches = [(i['name'],i.get('active','')=='*') for i in branches]
		branch_active, = [i for i,j in branches if j]
		if branch and branch != branch_active:
			raise NotImplementedError('dev: code_current can only check the branch, not switch it. '
				f'note: branch={branch}, branch_active={branch_active}')
		# via: https://stackoverflow.com/a/52307619/3313859
		result = bash(f'git -C {path} remote show origin',
			permit_fail=True,quiet=True)
		if re.findall('local out of date',result['stdout']):
			if not strict:
				print('warning: your code (%s) is out of date'%path)
			else:
				raise Exception('your local code (%s) is out of date!'%path)
	return get_git_hash(path=path)
