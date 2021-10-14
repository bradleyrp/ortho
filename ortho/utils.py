#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Utilities catchall.
"""

import os
import psutil
import pprint

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
	else: yield path,base

def delve(o,*k): 
	"""
	Return items from a nested dict.
	"""
	return delve(o[k[0]],*k[1:]) if len(k)>1 else o[k[0]]

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
