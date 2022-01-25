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

class YAMLIncludeBase(yaml.YAMLObject):
	"""A YAMLObject that loads another YAML file safely."""
	_loader_kind = yaml.Loader
	# we neglect a yaml_tag here or this will automatically register with
	#   pyyaml when we import ortho. this means that if you want to use
	#   this as a tag, subclass and add yaml_tag to set one. note that 
	#   for some reason we could not get this to work with yaml.add_constructor
	#   because the arguments were not correct. the use of yaml_tag and 
	#   YAMLObject are a nice way to globally register something with yaml 
	#   without excessive calls. this is a useful magic
	yaml_tag = None
	@classmethod
	def from_yaml(cls, loader, node):
		"""Load another YAML file at this node."""
		fn = loader.construct_scalar(node)
		with open(fn) as fp:
			data = yaml.load(fp.read(),Loader=cls._loader_kind)
		return data

class YAMLIncludeBaseSafe(yaml.YAMLObject):
	"""A YAMLObject that loads another YAML file safely."""
	_loader_kind = yaml.SafeLoader
	# see comment in YAMLInclude for instructions on tags
	yaml_tag = None

# ortho can provide this kind of YAMLObject
#   or alternately it could be imported directly
YAMLObject = YAMLObjectOverride
