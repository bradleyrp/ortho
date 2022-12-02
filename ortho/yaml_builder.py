#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
These tools will help building YAML schemes that fill in untagged objects entered by a user, enabling you to have an easy way to handle flexible inputs 
"""

import ruamel
import typing

class YAMLDocumentBuilder:
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
					tagged.append(cls.builder(**item))
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
		elif isinstance(outgoing,typing.List):
			return representer.represent_sequence(cls.yaml_tag,outgoing)
		else:
			raise ValueError(f'invalid data type: {type(outgoing)}')
