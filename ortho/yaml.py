#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import yaml
import re

class YAMLObjectOverride(yaml.YAMLObject):
	"""A YAMLObject that runs __init__."""
	@classmethod
	def from_yaml(cls, loader, node):
		"""
		Convert a representation node to a Python object.
		"""
		kwarg_error_msg = '__init__() got an unexpected keyword argument'
		arg_error = '__init__() missing 1 required positional argument'
		explain = ' while instantiating YAML constructor "%s": %s'
		arg_dict = loader.construct_mapping(node, deep=True)
		try: return cls(**arg_dict)
		except Exception as e:
			if re.match(
				kwarg_error_msg,
				str(e)):
				raise TypeError(kwarg_error_msg +
					explain%cls.__name__,str(e))
			elif re.match(
				arg_error,
				str(e)):
				raise AssertionError(arg_error + 
					explain%cls.__name__,str(e))
			else: raise

def use_yaml_init():
	"""
	This function makes the method above universal by making yaml.YAMLObject 
	act like ortho.YAMLObject.
	"""
	yaml.YAMLObject = YAMLObjectOverride

# ortho can provide this kind of YAMLObject
YAMLObject = YAMLObjectOverride
