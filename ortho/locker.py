#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Locker tools for managing the state and file locks.
"""

import time
import os
import fcntl
import errno
import datetime as dt
import copy
import json

from .utils import dictdiff

# click is part of the cli extra for ortho
try: import click
except: click = None

class SimpleFlock:
	"""
	Minimal flock implementation.
	"""
	# recall that nix file locks are advisory
	# this method is useful for protecting another file with a token lock file
	# via: https://github.com/derpston/python-simpleflock
	def __init__(self,path,timeout=None):
		self.path = path
		self.timeout = timeout
		self.fd = None
	def __enter__(self):
		self.fd = os.open(self.path,os.O_CREAT)
		start_t = time.time()
		while True:
			try:
				fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
				# lock acquired
				return
			except (OSError,IOError) as ex:
				# resource temporarily unavailable
				if ex.errno != errno.EAGAIN: 
					raise
				elif (self.timeout is not None and 
					time.time() > (start_t + self.timeout)):
					# exceeded timeout
					raise
			# arbitrary sleep interval
			time.sleep(0.5)
	def __exit__(self, *args):
		fcntl.flock(self.fd, fcntl.LOCK_UN)
		os.close(self.fd)
		self.fd = None
		# low effort unlocking
		try: os.unlink(self.path)
		except: pass

# yaml is an optional handler below
# dev: generalize the reader/writer for the state
# dev: make the cli requirement for yaml more consistent
#   note that we use yaml when we use the unpack flag
#   in state_user below
yaml = None
try: import yaml
except: pass

def statefile(name='state.yml',
	lock=True,log=False,unpack=True,watch=True,dest='state',
	statefile_ctx='STATEFILE',statefile_infer=None,
	click_pass=False,track=True,hook=None,verbose=False,loader=None):
	"""
	Decorator to supervise a state with file locks and loggin.

	This includes a connection to the click context so you can get the statefile
	name from the click context.
	"""
	if track and not unpack:
		raise Exception('you must set unpack if you want to track')
	if track and not watch:
		raise Exception('you must set watch if you want to track')
	if unpack and not yaml:
		raise Exception('unpack requires yaml')
	if loader and not callable(loader):
		raise Exception('loader must be a function')

	def repack_state(outgoing,statefile_out,fname,state_ptr):
		"""Write the state to the statefile."""
		if outgoing is None:
			# the outgoing dict is a pointer to the state we unpacked
			outgoing = state_ptr	
		elif not isinstance(outgoing,dict):
			print('error: outgoing object: %s'%str(outgoing))
			raise Exception(f'function {fname} '
				'returned an object that is not a dict but '
				'optima_state was called with unpack so we '
				'cannot repack the data properly. see error above.')
		# generate the output first otherwise you might risk blanking the file
		output = yaml.dump(outgoing)
		with open(statefile_out,'w') as fp:
			fp.write(output)

	def wrapper(func):
		def inner(*args,**kwargs):
			statefile_out = None
			# accept the click context as the leading argument in case we are
			#   using the context to convey the statefile as a CLI argument
			if click and len(args)>0 and isinstance(args[0],click.core.Context):
				if 'ctx' in kwargs:
					raise Exception('name collision on "ctx" when we move the '
						'click context to kwargs')
				# you can pass the click context onward if needed, otherwise it
				#   has already served its purpose by providing the state file.
				#   the click context could also provide a debug flag for the
				#   debug_click function, but if the state decorator is listed
				#   later in the sequence, then 
				ctx = args[0]
				if click_pass:
					kwargs['ctx'] = ctx
				args = args[1:]
				statefile_out = ctx.obj.get(statefile_ctx,name)
			if statefile_infer:
				statefile_out = statefile_infer()
			if not statefile_out:
				# use the default name if we did not get the statefile from the 
				#   ctx which comes from a parent click command or the 
				#   statefile_infer function
				statefile_out = name
			if 'statefile' in kwargs:
				raise Exception('argument collision on "statefile"')
			# fully resolve the statefile_out path, assume to be relative to cwd
			statefile_out = os.path.abspath(os.path.expanduser(statefile_out))
			# the lock file is hidden in the same folder
			statefile_lock = os.path.join(
				os.path.dirname(statefile_out),'.%s.lock'%
				os.path.basename(statefile_out))
			# if we are not unpacking, we just pass the statefile
			if not unpack:
				# put the state name in the kwarg
				kwargs[dest] = statefile_out
			else:
				if not os.path.isfile(statefile_out): state_data = {}
				else:
					if verbose: print(f'loading {statefile_out}')

					# hook to add constructors to yaml
					# alternative is to use ortho.YAMLObject in your code
					# note that you cannot use the default SafeLoader below
					#   while also using YAMLObject to make YAML constructors
					if loader: loader_out = loader()
					else: loader_out = yaml.SafeLoader

					with open(statefile_out,'r') as fp:
						state_data = yaml.load(fp,Loader=loader_out)
						if not state_data: state_data = {}
				# load the state data into the destination kwarg
				kwargs[dest] = state_data
			# separate locking and logging features
			if log and not lock:
				raise Exception('you must lock if you log')
			elif lock and log:
				with SimpleFlock(
					statefile_lock,timeout=3) as sf:
					if verbose: print(f'status: locked {statefile_out}')
					# dev: should we set a timezone
					ts = dt.datetime.fromtimestamp(
						time.time()).strftime('%Y.%m.%d.%H%M')
					log_detail = dict(
						call=func.__name__,
						args=copy.deepcopy(args),
						kwargs=copy.deepcopy(kwargs),
						when=ts)
					# do not log the entire state in the watch file. the state 
					#   is automatically included in the kwargs when we decorate
					#   the functions that use the state, so it would otherwise 
					#   appear here unless we remove it
					state_omit = log_detail['kwargs'].pop('state',{})
					# pop the click context from the copy otherwise we cannot 
					#   serialize the context. the `optima_state` function is
					#   mean to handle user interface functions
					try: log_detail['kwargs'].pop('ctx')
					except: pass
					try: 
						if unpack and track:
							# tracking changes by copying the previous state
							state_before = copy.deepcopy(state_data)
						this = func(*args,**kwargs)
						if unpack:
							if track:
								diff = dictdiff(state_before,state_data)
								log_detail['state_diff'] = diff
							repack_state(
								outgoing=this,
								statefile_out=statefile_out,
								fname=func.__name__,
								state_ptr=state_data)
					except:
						if watch:
							log_detail['fail'] = True
							with open(f'{statefile_out}.watch','a') as fp:
								# ensure we can serialize any classes
								# via: https://stackoverflow.com/a/64469761
								fp.write(json.dumps(
									log_detail,default=vars)+'\n')
						raise
					else:
						if watch:
							with open(f'{statefile_out}.watch','a') as fp:
								# ensure we can serialize any classes
								# via: https://stackoverflow.com/a/64469761
								fp.write(json.dumps(
									log_detail,default=vars)+'\n')
					if verbose: print('status: releasing lock ')
					return this
			elif lock and not log: 
				with SimpleFlock(
					f'.{statefile_out}.lock',timeout=3) as sf:
					if verbose: print(f'status: locked {statefile_out}')
					this = func(*args,**kwargs)
					if unpack:
						repack_state(
							outgoing=this,
							statefile_out=statefile_out,
							fname=func.__name__,
							state_ptr=state_data)
					if verbose: print('status: releasing lock {statefile_out}')
					return this
			else:
				this = func(*args,**kwargs)
				# dev: calls to unpack seem repetitive. not sure how to fix
				if unpack:
					repack_state(
						outgoing=this,
						statefile_out=statefile_out,
						fname=func.__name__,
						state_ptr=state_data)
				return this
		inner.__name__ = func.__name__
		inner.__doc__ = func.__doc__
		return inner
	return wrapper
