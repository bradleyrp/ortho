#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import time
import os
import fcntl
import errno

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
yaml = None
try: import yaml
except: pass

def state_user(statefile='state.yml',
	lock=False,log=False,unpack=False,
	dest='statefile',statefile_ctx='STATEFILE',
	click_pass=False):
	"""
	Decorator to supervise a state with file locks and loggin.

	This includes a connection to the click context so you can get the statefile
	name from the click context.
	"""

	def repack_state(outgoing,statefile_out,fname,state_ptr):
		"""Write the state to the statefile."""
		if outgoing is None:
			print('111')
			outgoing = state_ptr	
		elif not isinstance(outgoing,dict):
			print('error: outgoing object: %s'%str(outgoing))
			raise Exception(f'function {fname} '
				'returned an object that is not a dict but '
				'optima_state was called with unpack so we '
				'cannot repack the data properly. see error above.')
		with open(statefile_out,'w') as fp:
			fp.write(yaml.dump(outgoing))

	def wrapper(func):
		def inner(*args,**kwargs):
			# accept the click context as the leading argument in case we are
			#   using the context to convey the statefile as a CLI argument
			if len(args)>0 and isinstance(args[0],click.core.Context):
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
			statefile_out = ctx.obj.get(statefile_ctx,statefile)
			if not statefile_out:
				raise Exception('you must send the statefile through the CLI '
					'(via --state) or via the "statefile" kwarg to the '
					'decorator')
			if 'statefile' in kwargs:
				raise Exception('argument collision on "statefile"')
			# if we are not unpacking, we just pass the statefile
			if not unpack:
				# put the statefile name in the kwarg
				kwargs[dest] = statefile_out
			else:
				if not os.path.isfile(statefile_out): state_data = {}
				else:
					with open(statefile_out,'r') as fp:
						state_data = yaml.load(fp,Loader=yaml.SafeLoader)
						if not state_data: state_data = {}
				# load the state data into the destination kwarg
				kwargs[dest] = state_data
			# separate locking and logging features
			if log and not lock:
				raise Exception('you must lock if you log')
			elif lock and log:
				with SimpleFlock(
					f'.{statefile_out}.lock',timeout=3) as sf:
					print(f'status: locked on {statefile_out}')
					# dev: should we set a timezone
					ts = dt.datetime.fromtimestamp(
						time.time()).strftime('%Y.%m.%d.%H%M')
					log_detail = dict(
						call=func.__name__,
						args=copy.deepcopy(args),
						kwargs=copy.deepcopy(kwargs),
						when=ts)
					# pop the click context from the copy otherwise we cannot 
					#   serialize the context. the `optima_state` function is
					#   mean to handle user interface functions
					try: log_detail['kwargs'].pop('ctx')
					except: pass
					try: 
						this = func(*args,**kwargs)
						if unpack:
							repack_state(
								outgoing=this,
								statefile_out=statefile_out,
								fname=func.__name__,
								state_ptr=state_data)
					except:
						log_detail['fail'] = True
						with open(f'{statefile_out}.watch','a') as fp:
							fp.write(json.dumps(log_detail)+'\n')
						raise
					else:
						with open(f'{statefile_out}.watch','a') as fp:
							fp.write(json.dumps(log_detail)+'\n')
					print('status: releasing lock')
					return this
			elif lock and not log: 
				with SimpleFlock(
					f'.{statefile_out}.lock',timeout=3) as sf:
					print(f'status: locked on {statefile_out}')
					this = func(*args,**kwargs)
					if unpack:
						repack_state(
							outgoing=this,
							statefile_out=statefile_out,
							fname=func.__name__,
							state_ptr=state_data)
					print('status: releasing lock')
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