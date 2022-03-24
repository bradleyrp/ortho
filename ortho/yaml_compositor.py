#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

# the following code was modified by Ryan Bradley to support ortho.yaml_include
# original source via: https://github.com/\
#   Tristan-Sweeney-CambridgeConsultants/ccorp_yaml_include

"""
The MIT License (MIT)

Copyright (c) 2014-2018 Tristan Sweeney, Cambridge Consultants

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import types
import os
import io

# modified imports by rpb
# nb a rare use-case, in an ortho-dependent software called overspack, requires
#   that we use get_real_ruamel to find the ruamel that was installed as a
#   dependency of ortho, in a separate site-packages (site.getsitepackages) 
#   location because we are building the overspack package on top of Spack 
#   (https://spack.io) which rolls its own older version of ruamel.yaml so in
#   order to use our copy, we import it separately
try:
	
	import ruamel.yaml as yamlr
	from ruamel.yaml.nodes import ScalarNode, MappingNode, SequenceNode
	from ruamel.yaml.scalarstring import PlainScalarString
	if not hasattr(yamlr,'YAML'):
		raise ModuleNotFoundError('ruamel.yaml version is insufficient')

# custom ruamel importer for compatibility with overspack and Spack
except (ModuleNotFoundError,ImportError): 

	from .yaml import get_real_ruamel
	yamlr = get_real_ruamel(parent=True)
	ScalarNode = yamlr.nodes.ScalarNode
	MappingNode = yamlr.nodes.MappingNode
	SequenceNode = yamlr.nodes.SequenceNode
	PlainScalarString = yamlr.scalarstring.PlainScalarString

class CompositingComposer(yamlr.composer.Composer):
	compositors = { k: {} for k in (ScalarNode, MappingNode, SequenceNode)}

	@classmethod
	def add_compositor(cls, tag, compositor, *, nodeTypes=(ScalarNode,)):
		for nodeType in nodeTypes:
			cls.compositors[nodeType][tag] = compositor

	@classmethod
	def get_compositor(cls, tag, nodeType):
		return cls.compositors[nodeType].get(tag, None)

	def __compose_dispatch(self, anchor, nodeType, callback):
		event = self.parser.peek_event()
		compositor = self.get_compositor(event.tag, nodeType) or callback
		if isinstance(compositor, types.MethodType):
			return compositor(anchor)
		else:
			return compositor(self, anchor)

	def compose_scalar_node(self, anchor):
		return self.__compose_dispatch(anchor, ScalarNode, 
			super().compose_scalar_node)
	
	def compose_sequence_node(self, anchor):
		return self.__compose_dispatch(anchor, SequenceNode, 
			super().compose_sequence_node)
	
	def compose_mapping_node(self, anchor):
		return self.__compose_dispatch(anchor, MappingNode, 
			super().compose_mapping_node)

class ExcludingConstructor(yamlr.constructor.Constructor):
	filters = { k: [] for k in (MappingNode, SequenceNode)}

	@classmethod
	def add_filter(cls, filter, *, nodeTypes=(MappingNode,)):
		for nodeType in nodeTypes:
			cls.filters[nodeType].append(filter)

	def construct_mapping(self, node):
		node.value = [(key_node, value_node) 
			for key_node, value_node in node.value
				if not any(f(key_node, value_node) 
			for f in self.filters[MappingNode])]
		return super().construct_mapping(node)
	
	def construct_sequence(self, node):
		node.value = [value_node 
			for value_node in node.value 
				if not any(f(value_node) 
			for f in self.filters[SequenceNode])]
		return super().construct_sequence(node)

def include_compositor(self, anchor):
	event = self.parser.get_event()
	yaml = self.loader.fork()
	path = os.path.join(os.path.dirname(self.loader.reader.name), event.value)
	with open(path) as f:
		return yaml.compose(f)

def exclude_filter(key_node, value_node = None):
	value_node = value_node or key_node # copy ref if None
	return key_node.tag == '!exclude' or value_node.tag == '!exclude'

ExcludingConstructor.add_filter(
	exclude_filter, nodeTypes=(MappingNode, SequenceNode))

CompositingComposer.add_compositor(
	'!include', include_compositor)
