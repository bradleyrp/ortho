#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Utilities catchall.
"""

import os
import sys
import psutil
import pprint
import subprocess

def catalog(base,path=None):
	"""
	Traverse all paths in a nested dictionary. Returns a list of pairs: paths and values.
	Note that lists can be a child item; catalog does not expand the indices.
	"""
	if not path: path = []
	if isinstance(base,dict):
		for x in base.keys():
			local_path = path[:]+[x]
			for b in catalog(base[x],local_path): yield b
	# we yield tuples in case you want to use set to comparethe results
	else: yield tuple(path),base

def delve(o,*k): 
	"""
	Return items from a nested dict.
	"""
	return delve(o[k[0]],*k[1:]) if len(k)>1 else o[k[0]]

def delvetry(o,*k,default=None): 
	"""
	Return items from a nested dict.
	"""
	try: return delve(o,*k)
	except: return default

def delveset(o,*k,**kwargs): 
	"""
	Utility function for adding a path to a nested dict.
	"""
	value = kwargs.pop('value',None)
	if value==None: raise Exception('delveset needs a value')
	if kwargs: raise Exception('unprocessed kwargs %s'%str(kwargs))
	if len(k)==0: raise Exception('deepset needs a path')
	elif len(k)==1: 
		try: o[k[0]] = value
		except Exception as e:
			print('cannot make a delveset assignment of %s to %s'%(k[0],str(o)))
			raise 
	else:
		if k[0] not in o: o[k[0]] = {}
		delveset(o[k[0]],*k[1:],value=value)

def catalog_r(cat):
	"""Reverse a dict of a catalog into a dict."""
	out = {}
	for i,j in cat.items():
		delveset(out,*i,value=j)
	return out

def dictdiff(a,b):
	"""Take the diff between nested dictionaries."""
	cat_a = dict(catalog(a))
	cat_b = dict(catalog(b))
	keys_a = set(cat_a.keys())
	keys_b = set(cat_b.keys())
	# get the common paths to log changes
	changes_paths = set(keys_a).intersection(keys_b)	
	changes = {}
	for path in changes_paths:
		l = cat_a[path]
		r = cat_b[path]
		if l != r:
			changes[path] = (l,r)
	deletes = dict([(i,cat_a[i]) for i in keys_a - keys_b])
	adds = dict([(i,cat_b[i]) for i in keys_b - keys_a])
	out = {}
	if adds: out['+'] = adds
	if deletes: out['-'] = deletes
	if changes: out['~'] = changes
	for k,v in out.items(): 
		out[k] = catalog_r(v)
	return out

def script_packer(settings):
	"""
	Canonical method for extracting variables from scripts.
	"""
	"""
	Fuddy-duddies who disapprove should consult stack overflow, see:
		https://stackoverflow.com/questions/9759820/how-to-get-a-list-of-variables-in-specific-python-module\
		#comment65661810_9759842
		> How does one query this abominable API? dir(), hasattr(), and 
		getattr(), of course. Whenever the Pythonisticity of a question is 
		questioned, I sagely roll my eyes. A non-Pythonic solution considered 
		harmful in the common case may prove to be the only solution in edge 
		cases. Welcome to the real world.  
	"""
	return dict([(k,v) 
		for k,v in vars(settings).items() 
		if not k.startswith('_')])

class Struct:
	"""
	Convert a dictionary to a structure.
	via: https://stackoverflow.com/a/1305663 
	"""
	"""
	Note that somebody made an entire library for this, see:
	https://stackoverflow.com/a/24852544
	The library is called bunch and it has good serialization which is pretty
	important for performing these kinds of operations. Python seems to be 
	highly extensible in a fairly unique way. Everybody adds their own ways of
	almost changing the syntax.
	dev: write this up somewhere 
	"""
	# dev: rescue other items from factory
	def __init__(self, **entries):
		self.__dict__.update(**entries)
	def __repr__(self): 
		return pprint.pformat(self.__dict__)

def get_cpu_cores():
	"""
	Report the number of physical CPU cores (i.e. without hyperthreading).
	"""
	nnodes = os.environ.get('SLURM_NNODES')	
	nprocs = os.environ.get('SLURM_CPUS_PER_TASK')	
	if nnodes and nnodes!='1':
		raise Exception('SLURM says you have more than one node and this is '
			'wasteful because this is threaded only')
	elif nprocs: cpu_count = int(nprocs)
	else: cpu_count = psutil.cpu_count(logical=False)
	return cpu_count

def is_empty_function(func):
	"""Check if a function is empty."""
	# via: https://stackoverflow.com/a/58973125/3313859
	# note that your function could still return a constant and match with empty_func
	# however it cannot have any code
	def empty_func(): pass
	def empty_func_with_doc(): 
		"""Empty function with docstring.""" 
		pass 
	return (
		func.__code__.co_code == empty_func.__code__.co_code or 
		func.__code__.co_code == empty_func_with_doc.__code__.co_code)

def clipboard(cmd,strict=False):
	"""
	Copy something to the clipboard.
	"""
	# dev: silent error on Linux because this is not completed yet
	if sys.platform=='linux':
		if not strict: return
		raise NotImplementedError('clipboard is not implemented on Linux')
	elif sys.platform=='darwin':
		util = 'pbcopy'
		subprocess.run("pbcopy",universal_newlines=True,input=cmd)
	else:
		raise NotImplementedError('clipboard not configured for platform: %s'%
			sys.platform)
	return
