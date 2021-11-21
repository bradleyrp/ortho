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
		error_keys = [
			r'__init__\(\) got an unexpected keyword argument',
			r'__init__\(\) missing 1 required positional argument',
			r'.+takes no arguments',]
		explain = 'while instantiating YAML constructor "%s": %s'
		if node.__class__.__name__=='ScalarNode':
			kind = 'scalar'
			args_out = loader.construct_scalar(node)
		elif node.__class__.__name__=='MappingNode':
			args_out = loader.construct_mapping(node, deep=True)
			kind = 'mapping'
		else:
			raise Exception(f'invalid node type: {node}')
		try: 
			if kind == 'scalar':
				return cls(args_out)
			elif kind == 'mapping':
				return cls(**args_out)
			else: raise Exception
		except Exception as e:
			for error_key in error_keys:
				if re.match(
					error_key,
					str(e)):
					raise TypeError(explain%(cls.__name__,str(e)))
			else: raise

def use_yaml_init():
	"""
	This function makes the method above universal by making yaml.YAMLObject 
	act like ortho.YAMLObject.
	"""
	yaml.YAMLObject = YAMLObjectOverride

# ortho can provide this kind of YAMLObject
YAMLObject = YAMLObjectOverride
