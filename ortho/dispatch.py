#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import inspect
import sys
import pprint
from .logs import str_types
import functools

def introspect_function(func,**kwargs):
	"""
	Get arguments and kwargs expected by a function.
	"""
	# the self object remains in the argument list in old python
	selfless = lambda x: [i for i in x if i!='self']
	# previously we had a message warning against sending a string instead of a
	#   function. this might have had some utility in a previous version of this
	#   code in which we scan functions for their signatures (which we called 
	#   gleaning) before importing a piece of code. this method was abandoned 
	#   because it was fairly clunky
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
		sig = inspect.signature(func) # pylint: disable=no-member
		args_collect = tuple([key for key,val in sig.parameters.items() 
			if val.default==inspect._empty])
		# decorators add self to the argument list somehow so we filter
		packed = {'args':selfless(args_collect)}
		keywords = [(key,val.default) for key,val in sig.parameters.items() 
			if val.default!=inspect._empty]
		packed['kwargs'] = dict(keywords)
		# double double stars are not allowed
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

### HANDLER: class for multiple-dispatch by kwargs keys

handler_explain = """\
The `Handler` class is designed to perform multiple dispatch on class methods by
keyword argument name, not type.

The `Handler` class allows the subclass to define several similar methods \
which all take different arguments. When the class instance is "solved" via \
the `solve` property, the Handler selects the right function. The _protected \
keys are diverted into attributes common to all child class instances. For \
example the name and meta flags are common to all."""

class Handler(object):
	_is_Handler = True
	_taxonomy = {}
	# internals map to special structures in the Handler level
	# recently modified this so that we use underscores to distinguish these 
	#   items, since "name" is a very common key. this might break some 
	#   backwards compatibility with older codes which I am happy to 
	#   troubleshoot
	_internals = {'name':'_name','meta':'_meta'}
	# whether to allow inexact matching (we still prefer strict matching)
	lax = True
	# report keys
	verbose = False
	def _report(self):
		print('debug `Handler` summary follows: '+handler_explain)
		print('debug _protected keys not sent to methods: %s'%
			list(self._internals.keys()))
		if not self._taxonomy: print('debug There are no methods.')
		else: 
			for k,v in self._taxonomy.items():
				print('debug A method named "%s" has arguments: %s'%(k,v))
	def _matchless(self,args):
		"""Report that we could not find a match."""
		#! note that we need a more strict handling for the name keyword
		#!   which incidentally might be worth retiring
		name_child = self.__class__.__name__ 
		self._report()
		raise Exception(
			('%(name)s cannot classify instructions with '
				'keys: %(args)s. See the report above for details.'
			if not self.classify_fail else self.classify_fail)%
			{'args':args,'name':name_child})
	def _classify(self,*args):
		matches = [name for name,keys in self._taxonomy.items() if (
			(isinstance(keys,set) and keys==set(args)) or 
			(isinstance(keys,dict) and set(keys.keys())=={'base','opts'} 
				and (set(args)-keys['opts'])==keys['base']
				and (set(args)-keys['base'])<=keys['opts']))]
		if len(matches)==0: 
			if not self.lax: self._matchless(args)
			else:
				# collect method target that accept spillovers
				# where spillover means we have extra kwargs going to **kwargs
				# and not that we do not allow arguments in this dev stage
				spillovers = [i for i,j in self._taxonomy.items() 
					if j.get('kwargs',False)]
				spills = [(i,
					set.difference(set(args),set.union(j['base'],j['opts']))) 
					for i,j in self._taxonomy.items() if i in spillovers]
				if not spills: self._matchless(args)
				scores = dict([(i,len(j)) for i,j in spills])
				score_min = min(scores.values())
				matches_lax = [i for i,j in scores.items() if j==score_min]
				if len(matches_lax)==0: self._matchless(args)
				elif len(matches_lax)==1: return matches_lax[0]
				else:
					# if we have redundant matches and one is the default
					#   then the default is the tiebreaker
					#! the following logic needs to be checked more carefully
					if self._default and self._default in matches_lax: 
						return self._default
					# if no default tiebreaker we are truly stuck
					self._report()
					raise Exception('In lax mode we have redundant matches. '
						'Your arguments (%s) are equally compatible with these '
						'methods: %s'%(list(args),matches_lax))
		elif len(matches)>1: 
			raise Exception('redundant matches: %s'%matches)
		else: return matches[0]
	def _taxonomy_inference(self):
		"""
		Infer a taxonomy from constituent functions. The taxonomy enumerates
		which functions are called when required (base) and optional (opts)
		arguments are supplied. Historically we set the class attribute 
		taxonomy to specify this, but we infer it here.
		"""
		# note that all functions that start with "_" are invalid target methods
		methods = dict([(i,j) for i,j in 
			inspect.getmembers(self,predicate=inspect.ismethod)
			if not i.startswith('_')])
		expected = dict([(name,introspect_function(methods[name])) 
			for name in methods])
		# decorated handler subclass methods should save introspect as an attr
		for key in methods:
			if hasattr(methods[key],'_introspected'): 
				expected[key] = methods[key]._introspected
		#! fixed this in instrospect above for consistency
		if 0:
			#! this is not useful in python 3 because the self argument is 
			#!   presumably ignored by the introspection
			if sys.version_info<(3,0):
				for name,expect in expected.items():
					if 'self' not in expect['args']:
						print('debug expect=%s'%expect)
						raise Exception('function "%s" lacks the self argument'%
							name)
		# convert to a typical taxonomy structure
		self._taxonomy = dict([(name,{
			'base':set(expect['args']),
			'opts':set(expect['kwargs'].keys())
			}) for name,expect in expected.items()
			if not name.startswith('_')])
		"""
		exceptions to the taxonomy
		any functions with kwargs as a base argument via "**kwargs" are allowed
		to accept any arbitrary keyword arguments, as is the 
		"""
		for key in self._taxonomy:
			double_stars = expected[key].get('**',None)
			if double_stars: 
				self._taxonomy[key]['kwargs'] = True
		# check for a single default handler that only accespts **kwargs
		defaults = [i for i,j in self._taxonomy.items() 
			if j.get('kwargs',False) and len(j['base'])==0 
			and len(j['opts'])==0]
		if len(defaults)>1: 
			raise Exception('More than one function accepts only **kwargs: %s'%defaults)
		elif len(defaults)==1: self._default = defaults[0]
		else: self._default = None
		# check valid taxonomy
		# note that using a protected keyword in the method arguments can
		#   be very confusing. for example, when a method that takes a name
		#   is used, the user might expect name to go to the method but instead
		#   it is intercepted by the parent Handler class and stored as an
		#   attribute. hence we have a naming table called _internals and we
		#   protect against name collisions here
		collisions = {}
		for key in self._taxonomy:
			argnames = (list(self._taxonomy[key]['base'])+
				list(self._taxonomy[key]['opts']))
			collide = [i for i in self._internals.values()
				if i in argnames]
			if any(collide): collisions[key] = collide
		if any(collisions):
			# we print the internals so you can see which names you cannot use
			print('debug internals are: %s'%self._internals)
			raise Exception((
				'Name collisions in %s (Handler) method '
				'arguments: %s. See _internals above.')%(
					self.__class__.__name__,collisions))
		fallbacks = []
	def __init__(self,*args,**kwargs):
		if args: 
			raise Exception(
				'Handler classes cannot receive arguments: %s'%list(args))
		classify_fail = kwargs.pop('classify_fail',None)
		inspect = kwargs.pop('inspect',False)
		# safety check that internals include the values we require
		#   including a name and a meta target
		required_internal_targets = set(['meta','name'])
		if not set(self._internals.keys())==required_internal_targets:
			raise Exception(
				'Handler internals must map to %s but we received: %s'%(
				required_internal_targets,set(self._internals.keys())))
		name = kwargs.pop(self._internals['name'],None)
		meta = kwargs.pop(self._internals['meta'],{})
		self.meta = meta if meta else {}
		#! name is a common key. how are we using it here?
		if not name: self.name = "UnNamed"
		else: self.name = name
		# kwargs at this point are all passed to the subclass method
		# leaving taxonomy blank means that it is inferred from args,kwargs
		#   of the constitutent methods in the class
		if not self._taxonomy: self._taxonomy_inference()
		# allow a blank instance of a Handler subclass, sometimes necessary
		#   to do the taxonomy_inference first
		#! note that some use-case for Handler needs to be updated with inspect
		#!   in which we need the taxonomy beforehand. perhaps a replicator?
		if not kwargs and inspect: return
		self.classify_fail = classify_fail
		if self.verbose: print('status Handler has keys: %s'%kwargs.keys())
		fname = self._classify(*kwargs.keys())
		if self.verbose: print('status Handler calls `%s`'%fname)
		self.style = fname
		self.kwargs = kwargs
		if not hasattr(self,fname): 
			raise Exception(
				'development error: taxonomy name "%s" is not a member'%fname)
		# before we run the function to generate the object, we note the 
		#   inherent attributes assigned by Handler, the parent, so we can
		#   later identify the novel keys
		self._stock = dir(self)+['_stock','solution']
		# introspect on the function to make sure the keys 
		#   in the taxonomy match the available keys in the function?
		self.solution = getattr(self,fname)(**kwargs)
		# make a list of new class attributes set during the method above
		self._novel = tuple(set(dir(self)) - set(self._stock))
	def __repr__(self):
		"""Look at the subclass-specific parts of the object."""
		#! this is under development
		if hasattr(self,'_novel'): 
			report = dict(object=dict(self=dict([(i,getattr(self,i)) 
				for i in self._novel])))
			if self.meta: report['object']['meta'] = self.meta
			report['object']['name'] = self.name
			# dev: previously used treeview
			pprint.pprint(report)
			return "%s [a Handler]"%self.name
		else: return super(Handler,self).__repr__()
	@property
	def solve(self): 
		return self.solution
	@property
	def result(self): 
		# an alias for solve
		# instantiating a Handler subclass runs the function
		# the solve, result properties return the result
		return self.solution

def solver_handler(arg):
	"""Check if an object is a Handler and if so, solve it."""
	if getattr(arg,'_is_Handler',False):
		return arg.solve
	else: return arg

def incoming_handlers(func):
	"""
	Decorator which ensures that any incoming arguments or kwargs values
	which are Handlers are solved before they reach the function.
	This feature is very useful when connecting YAML object/apply tags to
	Handler subclasses.
	"""
	@functools.wraps(func)
	def func_out(*args,**kwargs):
		args = (solver_handler(arg) for arg in args)
		kwargs = dict([(i,solver_handler(j)) for i,j in kwargs.items()])
		return func(*args,**kwargs)
	func_out.__name__ = func.__name__
	return func_out

### DISPATCH: updated (simpler) class for multiple-dispatch by kwargs keys

def signature_match(sig,*args,**kwargs):
	"""Check if a function will accept a set of arguments."""
	fail = False
	n_args = len(args)
	# we have to pop from kwargs to see if there are extrana but if not
	#   then we need a full copy for testing the function call
	kwargs_popper = dict(kwargs)
	if n_args <= len(sig['args']):
		args_named = dict(zip(sig['args'],args))
		kwargs_popper.update(**args_named)
	# exit early if we have more args than the signature
	else: return False
	# step through signature arguments and search
	for anum,arg in enumerate(sig['args']):
		if anum >= n_args and arg not in kwargs:
			fail = True
			break
		else:
			# pop kwargs that correspond to args names
			try: kwargs_popper.pop(arg)
			except:
				import pdb;pdb.set_trace()
	# check for extraneous kwargs
	# critical bugfix here: previously we checked to see if the left was 
	#   greater than the right in:
	#     set(kwargs_popper.keys()) > set(sig['kwargs'])
	#   however if they are disjoint, this is false. what we really want is to
	#   see if any of the signature kwargs are not contained in the kwargs
	#   we received in this challenge. we could probably use this condition:
	#     not set(kwargs_popper.keys()) <= set(sig['kwargs'].keys())
	#   but it makes more intuitive sense to subtract and see if anything 
	#   remains outside
	if any(set(kwargs_popper.keys()) - set(sig['kwargs'].keys())):
		fail = True
	return not fail

def function_accepts_args(func,*args,**kwargs):
	"""Check if a function will accept a set of arguments."""
	# collect the signature
	sig = introspect_function(func)
	return signature_match(sig,*args,**kwargs)

def function_accepts_args_bind(func,*args,**kwargs):
	"""Check if a function will accept a set of arguments."""
	raise NotImplementedError('use bind to check and compare times')

class DispatcherBase:
	# dev: why is Dispatcher a parent class and not a decorator? a decorator
	#   might provide more definition-time options for checking things
	def __init__(self,*args,**kwargs):
		# store the incoming arguments
		self._args = args
		self._kwargs = kwargs
		# collect methods
		self._methods = dict([(i,j) for i,j in 
			inspect.getmembers(self,predicate=inspect.ismethod)
			if not i.startswith('_')])
		# identify a match
		matches = []
		for name,func in self._methods.items():
			if function_accepts_args(func,*self._args,**self._kwargs):
				matches.append(name)
		if not matches:
			raise Exception(('this subclass of Dispatcher (%s) does not have '
				'any functions capable of accepting the arguments you sent: '
				'args=(%s), kwargs=(%s)')%(
					self.__class__.__name__,str(args),str(kwargs)))
		elif len(matches)>1:
			raise NotImplementedError('redundant matches: %s'%str(matches))
		else: self._target = matches[0]

		"""
		experimental alternative: is solve necessary?
			when you subclass the DispatcherBase (formerly Dispatcher), you can
			define methods with different signatures and then if you create
			an object with e.g. MyClass(*args,**kwargs) then the
			DispatcherBase class will find the right method to match the
			signature. however, to return the object, you need to access the
			MyClass(*args,**kwargs).solve property. in the following
			commented code, I try to dynamically change once class into
			another. note that we cannot delete the methods because they are
			bound to the class, so the delattr example below is misguided.
			in general it's way way too hacky to try to dynamically change
			one class to another. eliminating the need for using the solve
			property to return the target object after signature dispatch is
			much easier when we create the Dispatcher decorator below
		"""
		# experimental alternative: dynamically change the class
		# self.me = getattr(self,self._target)(*self._args,**self._kwargs)
		# do not try to delattr the methods from an object, this is impossible
		# this does not work: 
		#   for key in self._methods.keys(): delattr(self,key)
		# here we dyanmically copy one instance into another
		# for key in vars(me):
		#     if not key.startswith('_'):
		#         setattr(self,key,getattr(me,key))
		# here we play a trick and rename the class
		# self.__class__ = me.__class__
		# note: do not use the above strategy because it is obviously hacky!

	@property
	def solve(self):
		return getattr(self,self._target)(*self._args,**self._kwargs)

class Dispatcher:
	def __init__(self,target_cls):
		# the container class has no constructor and only supplies methods
		self.container = target_cls()
	def __call__(self,*args,**kwargs):
		# the following sequence is nearly verbatim from Dispatcher.__init__
		# store the incoming arguments
		self._args = args
		self._kwargs = kwargs
		# collect methods
		self._methods = dict([(i,j) for i,j in 
			inspect.getmembers(self.container,predicate=inspect.ismethod)
			if not i.startswith('_')])
		# identify a match
		matches = []
		for name,func in self._methods.items():
			if function_accepts_args(func,*self._args,**self._kwargs):
				matches.append(name)
		if not matches:
			raise Exception(('this subclass of Dispatcher (%s) does not have '
				'any functions capable of accepting the arguments you sent: '
				'args=(%s), kwargs=(%s)')%(
					self.container.__class__.__name__,str(args),str(kwargs)))
		elif len(matches)>1:
			raise NotImplementedError('redundant matches in Dispatcher class '
				f'({self.container.__class__.__name__}): %s'%str(matches))
		else: self._target = matches[0]
		method_builder = getattr(self.container,self._target)
		result = method_builder(*args,**kwargs)
		return result

def check_local_frame(name,stack_depth=1):
	"""
	Get locals from the frame.
	This technique is required to perform multiple dispatch by signature.
	We later build a decorator that augments successive definitions of the same
	function in a single namespace.
	"""
	# inspired by https://github.com/kalekundert/signature_dispatch
	frame = inspect.currentframe()
	if frame is None:
		frame = inspect.stack()[stack_depth+1].frame
	else:
		for i in range(stack_depth+1):
			frame = frame.f_back
	try:
		locals = frame.f_locals
		if name in locals:
			return locals[name]
		else:
			return None
	finally: del frame

class DispatcherFunction:
	def __init__(self,):
		"""
		A function attribute which disambiguates multiple functions serving as
		endpoints for multiple dispatch by signature.
		"""
		self.candidates = []
		self.sigs = []
		self._name = None
	def add(self,func):
		if not self._name:
			self._name = func.__name__
		else:
			if self._name != func.__name__:
				raise Exception('name issue?')
		self.candidates.append(func)
		if not hasattr(func,'_sig'):
			func._sig = introspect_function(func)
		self.sigs.append(func._sig)
	def dispatch(self,*args,**kwargs):
		for snum,sig in enumerate(self.sigs):
			if signature_match(sig,*args,**kwargs):
				return self.candidates[snum](*args,**kwargs)
		# dev: this might be uninformative if you use it in a class, but I 
		#   cannot figure out how to get the class name, so in YAML load you 
		#   would have to do some tricky guesswork
		raise TypeError(
			f'function for has no match for args={args}, kwargs={kwargs}. '
			'recall that you cannot use @dispatcher on class methods')

def dispatcher(func):
	"""Decorator for multiple dispatch by signature."""
	# get the previously function definition
	prev = check_local_frame(func.__name__)
	# if we already have the supervisory class we add to it
	if prev:
		if hasattr(prev,'_multiplex'):
			mp = prev._multiplex
		else:
			mp = DispatcherFunction()
			mp.add(prev)
	else:
		if hasattr(func,'_multiplex'):
			mp = func._multiplex
		else:
			mp = DispatcherFunction()
	mp.add(func)
	func._multiplex = mp
	def wrapper(*args,**kwargs):
		if not hasattr(func,'_multiplex'):
			raise Exception('dispatcher failed')
		return func._multiplex.dispatch(*args,**kwargs)
	wrapper._multiplex = mp
	# announce the multiple dispatch
	if 0: print('overloading %s, id=%s'%(func.__name__,id(func)))
	return wrapper
