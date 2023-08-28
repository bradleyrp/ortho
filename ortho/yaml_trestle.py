#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
TRESTLE

Trestle is a pattern for building a mediated YAML file interaface in which a
user can add items to a YAML file which is read, modified, then rewritten in a
completed form. This automatically applies a template for different kinds of 
data and tends to streamline complicated user data entry interfaces.
"""

# note from the author to the author: do not, under any circumstances, unpack
#   any YAML objects yourself. do not touch the value attribute. keep the YAML
#   serializer totally separate. ignore this at your own peril!

import os
import ruamel
import typing
from .yaml import yaml_str

class TrestleDocumentXXX:
	yaml_tag = '!doc'
	def __init__(self,*,data):
		self.data = data

	@property
	def clean(self):
		return self.data

	@classmethod
	def from_yaml(cls,constructor,node):
		doc_kind = node.__class__.__name__
		if doc_kind == 'SequenceNode':
			data = ruamel.yaml.constructor.SafeConstructor.construct_sequence(
				constructor,node,deep=True)
			tagged = []
			for item in data:
				# check if yaml and build if not
				if hasattr(item,'yaml_tag'):
					tagged.append(item)
				else:
					# dictionaries are mapped to kwargs
					if isinstance(item,dict):
						tagged.append(cls.builder(**item))
					# sequences are mapped to args
					elif isinstance(item,(tuple,list)):
						tagged.append(cls.builder(*item))
					# otherwise we pass a single argument
					else:
						tagged.append(cls.builder(item))
		elif doc_kind == 'MappingNode':
			data = ruamel.yaml.constructor.SafeConstructor.construct_mapping(
				constructor,node,deep=True)
			tagged = {}
			for key,val in data.items():
				# check if yaml and build if not
				if hasattr(val,'yaml_tag'):
					tagged[key] = val
				else:
					tagged[key] = cls.builder(**val)
		else:
			raise ValueError(f'invalid document type {doc_kind}')
		# autotag constituents for this document
		return cls(data=tagged)

	@classmethod
	def to_yaml(cls,representer,node):
		outgoing = node.clean
		if isinstance(outgoing,dict):
			return representer.represent_mapping(cls.yaml_tag,outgoing)
		elif isinstance(outgoing,typing.Sequence):
			return representer.represent_sequence(cls.yaml_tag,outgoing)
		else:
			raise ValueError(f'invalid data type: {type(outgoing)}')

def build_trestle(*,tags,yaml,get_text_completer=False):
	"""
	Inject custom YAML tags in a parser that will then complete or audit the 
	file as the user constructs it.
	"""
	# dev: the trestle feature is a candidate for a move to ortho
	# create a round-trip YAML parser
	# note that our roundtripping uses custom tags so we cannot preserve spaces
	#   and comments, but this is a fair compromise, see 
	#   https://stackoverflow.com/q/74049751/3313859

	# register tags
	for tag in tags:
		if not hasattr(tag,'yaml_tag'):
			raise ValueError(f'object {tag} has no yaml_tag attribute')
		yaml.register_class(tag)

	def yaml_completer(path):
		if not os.path.isfile(path):
			raise FileNotFoundError(f'expecting a file at {path}')
		with open(path) as fp:
			text_cache = fp.read()
		data = yaml.load(text_cache)
		# hook to post process the data before dumping
		# note that the postprocessing is a critical feature
		if hasattr(data,'post'):
			data.post()
		# try to dump the file, now with tags
		try: 
			with open(path,'w') as fp:
			 	yaml.dump(data,fp)
		# rewrite the cached text if we cannot dump it to the file
		except Exception as e:
			print('warning: writing original data, exception incoming')
			with open(path,'w') as fp:
			 	fp.write(text_cache)
			raise
		# we mark that the document is validated by attaching its path
		data._path = path
		return data

	def yaml_completer_text(text):
		data = yaml.load(text)
		# hook to post process the data before dumping
		# note that the postprocessing is a critical feature
		if hasattr(data,'post'):
			data.post()
		return yaml_str(obj=data,yaml=yaml)

	# optionally return a text completer function
	if get_text_completer:
		return yaml_completer,yaml_completer_text
	else:
		return yaml_completer

class Trestle:
	"""
	Base class for round-trip YAML tagging and modification.
	"""
	# note that this class is very, very similar to TrestleDocument. the crucial
	#   difference is that we are subclassing this class to build arbitrary 
	#   nested objects which might be tagged. The TrestleDocument above is 
	#   instead also using a builder to construct certain types of root level
	#   objects where appropriate

	@classmethod
	def to_yaml(cls,representer,node):
		# the clean property prepares the data for export to yaml
		cleaned = node.clean
		try:
			if cleaned == None:
				# use a null string as a placeholder for null, however this
				#   must also have a tag or else it would be incomprehensible
				return representer.represent_scalar(cls.yaml_tag,'')
			elif isinstance(cleaned,dict):
				return representer.represent_mapping(cls.yaml_tag,cleaned)
			elif isinstance(cleaned,str):
				return representer.represent_scalar(cls.yaml_tag,cleaned)
			elif isinstance(cleaned,typing.Sequence):
				return representer.represent_sequence(cls.yaml_tag,cleaned)
			else:
				raise NotImplementedError('base class from tag '
					f'{cls.yaml_tag} cannot return {cleaned}')
		except:
			print(f'failed to write clean data {node.__dict__} with '
				f'tag {cls.yaml_tag}')
			raise

	@classmethod
	def from_yaml(cls,constructor,node):
		# mapping nodes are constructed deep
		if isinstance(node,ruamel.yaml.nodes.MappingNode):
			data = ruamel.yaml.constructor.SafeConstructor.construct_mapping(
				constructor,node,deep=True)
			try: 
				out = cls(**data)
			except TypeError as e:
				if 'unexpected' in str(e):
					raise Exception(
						f'exception when building class from yaml: '
						f'{cls}: {e}')
				raise
			return out
		elif isinstance(node,ruamel.yaml.nodes.SequenceNode):
			# nb this was the site of a tricky error in which we forgot to use
			#   a constructor, and touched the third rail of YAML, the value
			#   attribute. this motivated the warning a the top of the document
			args = ruamel.yaml.constructor.SafeConstructor.construct_sequence(
				constructor,node,deep=True)
			return cls(*args)
		# null values from tagged objects appear as null strings
		elif isinstance(node,ruamel.yaml.nodes.ScalarNode) and node.value=='':
			return cls()
		# if we are aleady a class instance, we pass through
		elif isinstance(node,cls):
			return node
		# we mark strings and other scalars when they are ingested so that we 
		#   can send everything to a Dispatcher
		elif isinstance(node,str):
			return cls(str=node)
		elif isinstance(node,float):
			return cls(float=node)
		elif isinstance(node,int):
			return cls(int=node)
		# sequence can come along too
		elif isinstance(node,typing.Sequence):
			return cls(*node)
		else:
			raise TypeError(f'unprepared to interpret type for {node}')

class TrestleDocument(Trestle):
	yaml_tag = None
	trestle_dispatcher = None
	trestle_kind = list
	trestle_name = 'data'
	def __init__(self,*args,**kwargs):
		"""
		Subclass this to tag a YAML document and send each object in the mapping
		or sequence to a Dispatcher for construction. This is built on the
		Trestle class, which serializes the YAML.
		"""
		if self.yaml_tag == None:
			raise Exception('this TrestleDocument requires a yaml_tag')
		if self.trestle_dispatcher == None:
			raise Exception('define a trestle_dispatcher class attribute that '
				'points to a Dispatcher which receives and builds the objects '
				f'for this document (kind: {self.trestle_kind})')
		if self.trestle_kind == list:
			data = []
			if kwargs:
				raise Exception(f'trestle document list got kwargs: {kwargs}')
			for child in args:
				# pass through tagged objects
				tag = getattr(child,'yaml_tag',None)
				item = self.trestle_dispatcher(**child) if not tag else child
				data.append(item)
		elif self.trestle_kind == dict:
			# dev: the following needs a test
			if args:
				raise Exception(f'trestle document dict got args: {kwargs}')
			data = {}
			for key,child in kwargs.items():
				# pass through tagged objects
				tag = getattr(child,'yaml_tag',None)
				item = self.trestle_dispatcher(**child) if not tag else child
				data[key] = item
		else:
			raise ValueError(f'invalid trestle_kind: {self.trestle_kind}')
		setattr(self,self.trestle_name,data)

	@property
	def clean(self):
		return getattr(self,self.trestle_name)

def trestle_nesting_typer(cls,obj):
	"""
	Helper to convert incoming types to the right class.
	This is necessary for classes that hold other YAML objects as attributes and
	therefore is required for nesting these structures in the YAML document. It
	should be used in the class constructors
	"""
	# if the object is already an instance of the class, it passes through
	if isinstance(obj,cls):
		return obj
	# null values also pass through
	elif obj == None:
		return None
	# if we receive a string, we use a send a "value" keyword to the constructor
	elif isinstance(obj,str):
		return cls(value=obj)
	# the dict is mapped to kwargs
	elif isinstance(obj,dict):
		return cls(**obj)
	# a list is sent to args
	elif isinstance(obj,typing.Sequence):
		return cls(*obj)
	# should we ever need to handle SequenceNode or Mapping node here
	elif isinstance(obj,ruamel.yaml.nodes.SequenceNode):
		args = ruamel.yaml.constructor.SafeConstructor.construct_sequence(obj)
		return cls(*args)
	elif isinstance(obj,ruamel.yaml.nodes.MappingNode):
		kwargs = ruamel.yaml.constructor.SafeConstructor.construct_mapping(obj)
		return cls(**kwargs)
	else:
		raise TypeError(
			f'cannot convert incoming object "{obj}" to class "{cls}"')
