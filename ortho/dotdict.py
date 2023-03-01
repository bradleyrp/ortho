#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import pickle

class DotDict(dict):
	"""
	Use dots to access dictionary items.
	Any key is allowed but only pythonic strings 
	Previous versions of this class used the `self.__dict__ = self` trick.
	Many thanks to: 
		https://stackoverflow.com/questions/47999145/48001538#48001538
	"""
	def __init__(self,*args,**kwargs):
		protect_keys = kwargs.pop('protected_keys',[])
		self._protect = set(dir(dict)+dir(object)+protect_keys)
		self._protect.add('_protect')
		super(DotDict,self).__init__(*args,**kwargs)
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__
	def __repr__(self): return str(dict([(i,self[i]) 
		for i in self.keys() if i not in self._protect]))
	def __dir__(self): 
		return [i for i in self.keys() if i not in self._protect 
			and isinstance(i,str_types)]

	# thanks ChatGPT for these two functions (__getstate__ and __setstate__) --Brock
	def __getstate__(self):
		# convert the object state to a dictionary
		state = self.__dict__.copy()
		state['__class__'] = self.__class__.__name__
		return state

	def __setstate__(self, state):
		# restore the object state from a dictionary
		clsname = state.pop('__class__')
		if clsname != self.__class__.__name__:
			raise ValueError("Invalid class name: {}".format(clsname))
		self.__dict__.update(state)

