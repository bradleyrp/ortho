#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import unittest
import functools
import pprint

from .dispatch import introspect_function
from .dispatch import function_accepts_args
from .dispatch import Handler
from .dispatch import Dispatcher
from .dispatch import DispatcherBase

# TEST: demonstrate the use of legacy Handler

class ActionH(Handler):
	def v1(self,a): return 'v1',(a,),{}
	def v2(self,a,b,c=None): return 'v2',(a,b,),{'c':c}

class TestHandler(unittest.TestCase):
	"""Test the legacy Handler class."""
	def test_handler_legacy(self):
		self.assertEqual(ActionH(a=1).solve,('v1',(1,),{}))
		self.assertEqual(ActionH(a=1,b=2).solve,('v2',(1,2,),{'c':None}))
		self.assertEqual(ActionH(a=1,b=2,c=3).solve,('v2',(1,2,),{'c':3}))
	def test_handler_legacy_arguments(self):
		with self.assertRaisesRegex(Exception,
			'cannot receive arguments'):
			ActionH(1,2).solve

# TEST: demonstrate that functools.wraps does not preserve signatures

def v0(a): pass
def v1(a): pass
def v1b(a,b): pass
def v2(a,b,c): pass
def v3(a,b,c=None): pass
def v4(a=None,b=None,c=None): pass

def func_reporter_bare(func,*args,**kwargs):
	"""
	This bare reporter function can be transformed into a decorator if you
	decorate it with decorator.decorator so that the func signature is 
	preserved.
	"""
	# suppressing printing for now. this decorator is for demo only
	if 0: print('status called "%s" with: args=%s, kwargs=%s'%(
		func.__name__,str(args),str(kwargs)))
	return func(*args,**kwargs)

def func_reporter_functools(func):
	"""
	Decorate a function with functools.wraps to demonstrate a critical
	weakness, namely that functools.wraps does not preserve the signature
	in a way that allows us do to introspection from ortho.handler.
	"""
	@functools.wraps
	def inner(*args,**kwargs):
		# suppressing printing for now. this decorator is for demo only
		if 0: print('status called "%s" with: args=%s, kwargs=%s'%(
			func.__name__,str(args),str(kwargs)))
		return func(*args,**kwargs)
	inner.__name__ = func.__name__
	inner.__doc__ = func.__doc__
	return inner

def test_decorator(reporter_func):
	# test arguments
	examples = [
		((),{'a':1,}),
		((),{'a':1,'b':2}),
		((),{'a':1,'c':3}),]
	# define test functions
	funcs_toc = dict([(i.__name__,i) for i in [v0,v1,v1b,v2,v3,v4]])
	sigs = {}
	# decorate with a reporter
	for name,func in funcs_toc.items():
		# beware: this function came from a script, and the script used globals.
		#   since I placed the functools.wraps test (which fails to preserve the
		#   signature) below the test which used decorator.decorator (which 
		#   succeeds), and originally kept globals below to automatically 
		#   decorate my functions, I found that functools.wraps was passing 
		#   because the functions were already decorated by decorator.decorator.
		#   this is why we run tests, to be sure about what works. I switched
		#   to locals here and all is well. then later I made it a dict because
		#   docs https://docs.python.org/3/library/functions.html#locals say 
		#   not to modify locals
		# recall that modifying globals is always allowed, see:
		#   https://stackoverflow.com/a/5958992
		funcs_toc[name] = reporter_func(func)
		sigs[name] = introspect_function(func)
	results = {}
	for enum,(args,kwargs) in enumerate(examples):
		for name,sig in sigs.items():
			func = funcs_toc[name]
			if function_accepts_args(func,*args,**kwargs):
				if enum not in results:
					results[enum] = []
				results[enum].append(name)
				func(*args,**kwargs)
	return results

class TestFuncTools(unittest.TestCase):
	def test_functools_introspect_issue(self):
		"""
		Contrast the use of decorator helpers (the "decorator" package vs 
		`functools.wraps`) when making decorated functions that are a part of
		a "multiple dispatch by signature" feature offered by `ortho.handler`.
		"""
		pass_result = {0:['v0','v1','v4'],1: ['v1b','v3','v4'],2:['v4']}
		try: 
			import decorator
			# manually decorate the bare function if decorator is available
			func_reporter_decorator = decorator.decorator(func_reporter_bare)
			self.assertEqual(
				test_decorator(func_reporter_decorator),
				pass_result)
		except: pass
		self.assertEqual(test_decorator(func_reporter_functools),{})

# TEST: use the DispatcherBase, an updated version of Handler

class ActionD(DispatcherBase):
	def v1(self,a): return 'v1',(a,),{}
	def v2(self,a,b,c=None): return 'v2',(a,b),{'c':c}
	# following two are redundant and cause an expected error
	def v3(self,a,b,c,d): return 'v3',(a,b,c,d,),{}
	def v4(self,a,b,c,d,e=None): return 'v4',(a,b,c,d),{'e':e}

class TestDispatcherClassBase(unittest.TestCase):
	"""
	Test the Dispatcher class.
	This class has the same API as Handler, with simpler code.
	This test is nearly identical to TestHandler.
	"""
	def test_handler_legacy(self):
		self.assertEqual(ActionD(a=1).solve,('v1',(1,),{}))
		self.assertEqual(ActionD(a=1,b=2).solve,('v2',(1,2,),{'c':None}))
		self.assertEqual(ActionD(a=1,b=2,c=3).solve,('v2',(1,2,),{'c':3}))
		self.assertEqual(ActionD(1,2).solve,('v2',(1,2,),{'c':None}))
	def test_handler_legacy_arguments(self):
		with self.assertRaisesRegex(Exception,
			'does not have any functions capable of accepting the arguments'):
			ActionD(1,2,3)
		with self.assertRaisesRegex(Exception,
			'redundant matches'):
			ActionD(1,2,3,4)

# TEST: dispatcher decorator

from ortho.dispatch import dispatcher

@dispatcher
def func_dispatch(a): return 'v1',(a,),{}
@dispatcher
def func_dispatch(a,b,c=None): return 'v2',(a,b),{'c':c}
@dispatcher
def func_dispatch(a,b,c,d): return 'v3',(a,b,c,d,),{}
@dispatcher
def func_dispatch(a,b,c,d,e=None): return 'v4',(a,b,c,d),{'e':e}

class TestDispatcher(unittest.TestCase):
	"""
	Test the dispatcher decorator.
	This resembles the signature_dispatch example below.
	"""
	def test_handler_legacy(self):
		self.assertEqual(func_dispatch(a=1),('v1',(1,),{}))
		self.assertEqual(func_dispatch(a=1,b=2),('v2',(1,2,),{'c':None}))
		self.assertEqual(func_dispatch(a=1,b=2,c=3),('v2',(1,2,),{'c':3}))
		self.assertEqual(func_dispatch(1,2),('v2',(1,2,),{'c':None}))
		# note that the dispatcher decorator can handle more ambiguity
		self.assertEqual(func_dispatch(1,2,3,4),('v3',(1,2,3,4),{}))
		self.assertEqual(func_dispatch(1,2,3,4,e=5),('v4',(1,2,3,4),{'e':5}))
	def test_handler_legacy_arguments(self):
		with self.assertRaisesRegex(Exception,
			'function has no match'):
			func_dispatch(1,2,3)
		with self.assertRaisesRegex(Exception,
			'function has no match'):
			func_dispatch(1,2,3,4,5)

# TEST: demonstrate the use of signature_dispatch
# note that the `signature_dispatch` package covers almost all of ortho.Handler
#   albeit with an alternate syntax. it covers @dispatcher functionality while
#   also including the option for priority
# see also functools.singledispatch and the multipledispatch package

# example functions
def x1(a): return {'a':a}
def x2(b): return {'b':b}

class TestSignatureDispatch(unittest.TestCase):
	def test_signature_dispatch(self):
		"""
		Demonstrate the use of the signature_dispatch package which covers
		much of the same utility as ortho.Handler
		"""
		pass_result = {0:['v0','v1','v4'],1: ['v1b','v3','v4'],2:['v4']}
		try:
			import signature_dispatch
			# use globals to demonstrate
			@signature_dispatch
			def my_func(*,a): return {'a':a}
			@signature_dispatch
			def my_func(*,b): return {'b':b}
			self.assertEqual(my_func(a=1),{'a':1})
			self.assertEqual(my_func(b=2),{'b':2})
			@signature_dispatch(priority=10)
			def my_func(*,a): return {'a_high_prio':a}
			self.assertEqual(my_func(a=1),{'a_high_prio':1})
		except ModuleNotFoundError: pass

# TEST: use the Dispatcher,
# the Dispatcher is a simple class decorator for multiple dispatch by signature

@Dispatcher
class Action:
	def v1(self,a): return 'v1',(a,),{}
	def v2(self,a,b,c=None): return 'v2',(a,b),{'c':c}
	# following two are redundant and cause an expected error
	def v3(self,a,b,c,d): return 'v3',(a,b,c,d,),{}
	def v4(self,a,b,c,d,e=None): return 'v4',(a,b,c,d),{'e':e}

class TestDispatcherClass(unittest.TestCase):
	"""
	Test the Dispatcher class.
	This class has the same API as Handler, with simpler code.
	This test is nearly identical to TestHandler.
	"""
	# nb the tests below are verbatim identical to the DispatcherBase tests
	#   however we omit the solve property required there to return the object
	#   and thereby demonstrate that the Dispatcher class decorator is the
	#   most elegant way to handle multiple dispatch by signature
	def test_handler_legacy(self):
		self.assertEqual(Action(a=1),('v1',(1,),{}))
		self.assertEqual(Action(a=1,b=2),('v2',(1,2,),{'c':None}))
		self.assertEqual(Action(a=1,b=2,c=3),('v2',(1,2,),{'c':3}))
		self.assertEqual(Action(1,2),('v2',(1,2,),{'c':None}))
	def test_handler_legacy_arguments(self):
		with self.assertRaisesRegex(Exception,
			'does not have any functions capable of accepting the arguments'):
			ActionD(1,2,3)
		with self.assertRaisesRegex(Exception,
			'redundant matches'):
			ActionD(1,2,3,4)
