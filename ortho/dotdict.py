#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

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
