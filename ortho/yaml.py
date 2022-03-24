#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import yaml
import re
from .utils import catalog

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

### FEATURE: cleaning incoming yaml

# to import and apply tags we need to clean

def recursive_clean(item):
	"""
	Clean (i.e. resolve) YAML objects into Python objects.
	"""
	if isinstance(item,(tuple,list)):
		up = []
		for i in item:
			up.append(recursive_clean(i))
	elif isinstance(item,dict):
		up = {}
		for k,v in item.items():
			up[k] = recursive_clean(v)
	else:
		up = item.clean if hasattr(item,'clean') else item
	return up

# dev: this class decorator only cleans incoming arguments and may not be
#   generally useful
def decorate_clean_class(func):
	"""
	Decorator to ensure extension classes clean incoming objects.
	"""
	def inner(self,*args,**kwargs):
		args = recursive_clean(args)
		kwargs = recursive_clean(kwargs)
		return func(self,*args,**kwargs)
	inner.__name__ = func.__name__
	inner.__doc__ = func.__doc__
	return inner

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

def get_real_ruamel(typ='rt',parent=False):
	"""
	Collect a round-trip YAML parser from the ruamel.yaml installed with
	this copy of ortho, specifically to avoid an internal dependency between 
	Spack and an older copy of ruamel.yaml which limits the feature set.
	See the use of this function in ortho.yaml_compositor for more detail.
	"""
	import sys
	import site
	# move ruamel out of the way
	for key in list(sys.modules.keys()):
		if key.startswith('ruamel'):
			sys.modules['base_ruamel.'+key] = sys.modules.pop(key)
	sys_path = list(sys.path)
	# get the ruamel from our site packages, i.e. the one that supports ortho
	sys.path = site.getsitepackages()
	import ruamel.yaml as ruamel_latest_yaml
	sys.path = sys_path
	# move the new ruamel out of the way
	for key in list(sys.modules.keys()):
		if key.startswith('ruamel'):
			sys.modules['ruamel_real.'+key] = sys.modules.pop(key)
	# move the original ruamel back
	for key in list(sys.modules.keys()):
		match = re.match(r'base_ruamel\.(.+)$',key)
		if match:
			sys.modules[match.group(1)] = sys.modules.pop(key)
	if not parent: 
		# make a ruamel round-trip parser
		yamlr = ruamel_latest_yaml.YAML(typ=typ)
		return yamlr
	else: 
		return ruamel_latest_yaml
	
def collect_anchors(data):
	"""
	Collect YAML anchors using ruamel.yaml round-trip parsing.
	This facilitates the !include_anchors_from functionality.
	"""
	index = {}
	cat = list(catalog(data))
	for key,val in cat:
		# store ruamel objects with an anchor value in an index
		if (val.__class__.__module__.startswith('ruamel.yaml') and 
			val.anchor.value):
			index[val.anchor.value] = val
	return index

# begin DEPRECATED code: working on include-like functionality which was
#   ultimately superceded by ortho.yaml_include

class YAMLAnchorInclude:
	"""
	Include YAML anchors from another file.
	Requires ruamel.yaml for extraction.
	"""
	yaml_tag = '!include_anchors'
	def __init__(self,source):
		raise NotImplementedError('this code is DEPRECATED')
		self.source = source
	@classmethod
	def from_yaml(cls,constructor,node):
		with open(node.value) as fp:
			yaml_this = get_real_ruamel()
			data = yaml_this.load(fp.read())
		index = collect_anchors(data)
		return index

def collect_anchors_tags(*funcs,yaml,yaml_object=None):
	"""
	Collect YAML anchors after resolving tags.
	"""
	# dev: abandoned because it is too hard to resolve tags and control anchors
	raise NotImplementedError('this code is DEPRECATED')
	# dev: deprecated
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
				cleaned = (outgoing.clean if hasattr(outgoing,'clean') 
					else outgoing)
				if hasattr(node,'anchor'):
					index_anchors[node.anchor] = cleaned
				return cleaned
		name_out = name+'Out'
		DerivedClass.__name__ = name_out
		taggers[name_out] = DerivedClass
	# define an anchor collector for general use, outside of tags
	def anchor_collect(data):
		"""
		Collect extraneous anchors in a dict from a round-trip
		ruamel.yaml parsing.
		"""
		index = {}
		cat = list(catalog(data))
		for key,val in cat:
			if (val.__class__.__module__.startswith('ruamel.yaml') and 
				val.anchor.value):
				if 1:
					index[val.anchor.value] = (
						val.clean if hasattr(val,'clean') else val)
				else:
					index[val.anchor.value] = val
		return index
	return dict(tags=taggers,index=index_anchors,collector=anchor_collect)

def build_yaml_linker():
	raise NotImplementedError('this code is DEPRECATED')
	yamlr = get_real_ruamel(parent=True)
	# inherit from ruamel.yaml
	class Composer(yamlr.composer.Composer):
		def __init__(self, loader=None):
			# type: (Any) -> None
			self.loader = loader
			if (self.loader is not None and 
				getattr(self.loader, '_composer', None) is None):
				self.loader._composer = self
			self.anchors = getattr(self.loader,'_anchors',{})
	class YAML(yamlr.YAML):
		def __init__(self, *args, **kwargs):
			self._anchors = kwargs.pop('anchors',{})
			super().__init__(*args, **kwargs)
			self.Composer = Composer
	return YAML

# end deprecated code
