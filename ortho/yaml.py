#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import yaml
import re

### FEATURE: use the constructor in yaml_tag classes with pyyaml

class YAMLObjectOverride(yaml.YAMLObject):
	"""
	A YAMLObject that runs __init__.

	A brief note on YAML conventions. The YAMLObjectOverride which appears as
	ortho.YAMLObject will allow you to use the __init__ function in derived 
	classes. This is ultimately just a shorthand that makes the derived classes
	look more like normal classes. The standard YAML convention in both pyyaml
	and ruamel.yaml is to use __init__ simply to set member variables. If you
	consult test_yaml.OrthoYAMLOverrides you can see some tests where we 
	demonstrate that the class constructor is ignored. This class forces pyyaml
	to ignore it. It is important to also note the test_yaml.RuamelOrtho tests
	which are designed to demonstrate the standard method for avoiding these 
	restrictions on the pyyaml YAMLObject constructor, namely the use of the
	`from_yaml` and `to_yaml` class methods to implement the desired logic. The 
	user should take advantage of ortho.YAMLObject to write classes in the style
	given by positive tests in test_yaml.OrthoYAMLOverrides, otherwise we 
	recommend the standard method and specifically the ruamel.yaml round trip 
	extensions for all advanced methods (particularly `collect_anchors`).
	"""
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
		elif node.__class__.__name__=='SequenceNode':
			args_out = loader.construct_sequence(node, deep=True)
			kind = 'sequence'
		else:
			raise Exception(f'invalid node type: {node}')
		try:
			if kind == 'scalar':
				return cls(args_out)
			elif kind == 'sequence':
				return cls(*args_out)
			elif kind == 'mapping':
				return cls(**args_out)
			else: raise Excepion
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
#   or alternately it could be imported directly
YAMLObject = YAMLObjectOverride

### FEATURE: include YAML files in other YAML files using pyyaml

class YAMLIncludeBase(yaml.YAMLObject):
	"""A YAMLObject that loads another YAML file safely."""
	_loader_kind = yaml.Loader
	# we neglect a yaml_tag here or this will automatically register with
	#   pyyaml when we import ortho. this means that if you want to use
	#   this as a tag, we subclass and add yaml_tag to set one. note that 
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

### FEATURE: use ruamel.yaml to extract a dict of anchors

def get_real_ruamel():
	"""
	Collect a round-trip YAML parser from the ruamel.yaml installed with
	this copy of ortho, specifically to avoid an internal dependency between 
	Spack and an older copy of ruamel.yaml which limits the feature set.
	"""
	import sys
	import site
	# move ruamel out of the way
	for key in list(sys.modules.keys()):
		if key.startswith('ruamel'):
			sys.modules['ruamel_base.'+key] = sys.modules.pop(key)
	sys_path = list(sys.path)
	# get the ruamel from our site packages, i.e. the one that supports ortho
	sys.path = site.getsitepackages()
	import ruamel.yaml as ruamel_latest_yaml
	sys.path = sys_path
	# make a ruamel round-trip parser
	yamlr = ruamel_latest_yaml.YAML(typ='rt')
	return yamlr
	
def collect_anchors(*funcs,yaml_object=None):
	# this method requires ruamel to access anchors. we can import it here 
	#   by default, in which case yaml_object can decorate any classes used
	#   by any derivative of ruamel.yaml.YAML otherwise the user should pass 
	#   it in, possibly using the get_real_ruamel function, whic was designed 
	#   specifically to avoid an internal dependency by Spack on an older 
	#   version of ruamel
	if not yaml_object:
		from ruamel.yaml import yaml_object
	index_anchors = {}
	taggers = {}
	for func_this in funcs:
		name = func_this.__class__.__name__
		@yaml_object(yaml)
		class DerivedClass(func_this): 
			yaml_tag = func_this.yaml_tag
			@classmethod
			def from_yaml(cls,constructor,node):
				outgoing = super(
					DerivedClass,cls).from_yaml(constructor,node)
				cleaned = outgoing.clean
				if hasattr(node,'anchor'):
					index_anchors[node.anchor] = cleaned
				return cleaned
		name_out = name+'Out'
		DerivedClass.__name__ = name_out
		taggers[name_out] = DerivedClass
	return dict(tags=taggers,index=index_anchors)
