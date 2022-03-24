#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Extend ruamel.yaml to allow include files or injection of a namespace when
loading a YAML file. This functionality is critical for leveraging the elegant
YAML file standard in a modular, DRY way.

Motivation:

- A StackOverflow answer (https://stackoverflow.com/a/18871178/3313859) explains
  that the YAML 1.2 spec forbids sharing anchors and aliases across documents. 
  The specification (https://yaml.org/spec/1.2-old/spec.html#id2800132) is 
  quite clear about this. And yet!

- We want to reuse YAML items across files in an ortho-dependent project called
  overspack. We understand that this exceeds the YAML specification however we
  do not care and YAML is too useful to replace and this "include" functionality
  is critical for DRY in our workflow.

- Anthon, the author of ruamel.yaml, claims that you have to include files
  in an inverse fashion (https://stackoverflow.com/a/44913652) which can
  be highly clumsy. In short, it seems you need to have the file which defines
  the anchors import the one which uses it, which is counterintuitive, or you
  would have to have a third file import both. We want to avoid

- An answer on the same StackOverflow question led me to the most robust 
	solution (https://stackoverflow.com/a/55975390/3313859) which I added to a 
	sibling code (yaml_compositor.py).

- I extended this code to accept a "namespace" object from Python which
  gets anchors before it is included in the target YAML object. This feature
  means that we can load in our own anchors as well.

This code requires ruamel.yaml and utilizes code which is copyright 2014-2018 
Tristan Sweeny and distributed under the MIT license, see yaml_compositor.py 
for the source code. The yaml_compositor.py is an extremely elegant way to 
extend ruamel.yaml to allow the unorthodox include file feature.
"""

import io

# we handle ruamel.yaml imports over in yaml_compositor
from .yaml_compositor import (
	CompositingComposer, ExcludingConstructor, yamlr, PlainScalarString)

def decorate_root_anchors(namespace):
	"""
	Serialize a dict and decorate all root-level keys with coterminus
	anchors. The result is consumed by the ortho.yaml.inject_compositor
	which can be accessed via ortho.yaml_include.YAML with the !inject
	tag to embed a namespace from Python inside a YAML file.
	"""
	# we must use roundtrip to set anchors below
	yaml_this = yamlr.YAML(typ='rt',pure=True)
	stream = io.StringIO()
	yaml_this.dump(namespace,stream)
	stream.seek(0)
	ns = yaml_this.load(stream)
	for key,val in ns.items():
		if isinstance(val,str):
			ns[key] = PlainScalarString(
				val,anchor=key)
			val = ns[key]
		else:
			val.yaml_set_anchor(key)
			val.anchor.always_dump = True
	# return the namespace along with the yaml instance we are loading 
	#   and dumping with in case we want to stream this somewhere else
	return ns,yaml_this

def inject_compositor(self, anchor):
	"""
	Inject a namespace with root keys that point to anchors of the same name.
	"""
	event = self.parser.get_event()
	ns_in = self.ns
	yaml = self.loader.fork()
	if not isinstance(ns_in,io.IOBase):
		ns,yaml_this = decorate_root_anchors(ns_in)
		ns_stream = io.StringIO()			
		yaml_this.dump(ns,ns_stream)
		ns_stream.seek(0)
		with ns_stream as f:
			return yaml.compose(f)
	else: 
		ns_stream = ns_in
		with ns_stream as f:
			return yaml.compose(f)

class YAML(yamlr.YAML):
	def __init__(self, *args, **kwargs):
		ns = kwargs.pop('ns',None)
		super().__init__(*args, **kwargs)
		self.Composer = CompositingComposer
		self.Constructor = ExcludingConstructor
		# the namespace is conveyed to the composer
		self.Composer.ns = ns
		# the YAML instance is saved for serialization in inject_compositor
		self.Composer._parent = self

	def fork(self):
		yaml = type(self)(typ=self.typ, pure=self.pure)
		yaml.composer.anchors = self.composer.anchors
		return yaml

CompositingComposer.add_compositor(
	'!inject', inject_compositor)
