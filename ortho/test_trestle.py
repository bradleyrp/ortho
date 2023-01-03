#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

# dev: improve error handling, consider writing errors to the yaml

"""
TRESTLE
An adaptive YAML-based user-interface to complex data structures.

In this test, I will demonstrate the use of the "trestle" method in which we
build an interface to a YAML document using tags that can either automatically 
fill in standardized components, or at least validate that the user had added 
data correctly. The tags can also be connected to other programs, and hence they
serve as a two-way API: the user can add data, the tags can validate it, and 
then you can connect these to downstream behaviors. The YAML file thereby acts
as an *ad hoc* database that is easy to interact with. I find that it can take
the place of a complicated command line interface by accomodating very rich 
data entry which also follows constraints. Expansion into a more fully-featured
API pattern will be forthcoming once I use this method in more applications.

Note that I built this script very easily in another interactive script via:

	python -m ortho interact -i test-trestles.py

That test is omitted in favor of a proper test below. The interact feature is
useful for development.
"""

import io
import sys
import unittest

from . import build_trestle, BaseTrestle, TrestleDocument
from . import Dispatcher
from . import build_trestle

# STEP 1: Build a Dispatcher to transform root-level objects

@Dispatcher
class MyIndexBuilder:
	"""
	Transform root-level objects in the document via multiple dispatch by
	signature.
	"""
	def kind_a(self,*,a,b,c=None):
		"""
		The primary scanner entry is a text file bound to scanner tasks.
		"""
		return HandlerA(a=a,b=b,c=c)

	def kind_b(self,*,e,f,g=None):
		"""
		A request to collect all unscanned files.
		"""
		return HandlerB(e=e,f=f,g=g)

# STEP 2: Write a class to manage your document
# This class makes it possible to write functions that integrate across the 
#   YAML-tagged objects, which otherwise cannot "look up" to see their parents.
#   It is also important to perform document-wide interpretation of the
#   constituents of the file. We must select either a mapping or sequence for 
#   the root level of our document.

# save the global keys before defining objects with yaml_tag
keys_globals = set(globals().keys())

class MyIndex(TrestleDocument): 
	"""
	Supervise index file.
	"""
	yaml_tag = '!my_doc'
	builder = MyIndexBuilder

	def post(self):
		print('status: we are inside the special "post" hook for the '
			f'{self.__class__.__name__} class where we can access '
			'self.data to perform across-child actions')

# STEP 3: Write a semi-generic type handler
# The following serves as the base class for the YAML objects you will serialize
#   to build your document. It ensures that we can manage different input and 
#   output types properly. This is the primary interface to the YAML library.

class ScannerYAML(BaseTrestle):
	"""Base class for round-trip YAML tagging and modification."""
	pass

class HandlerA(ScannerYAML):
	yaml_tag = '!kind_a'
	def __init__(self,*,a,b,c=None):
		self.a = a
		self.b = b
		self.c = c
		print('status: we are in the HandlerA constructor')
	@property
	def clean(self):
		out = dict(a=self.a,b=self.b)
		if self.c:
			out['c'] = self.c
		return out

class HandlerB:
	yaml_tag = '!kind_b'
	def __init__(self,*,e,f,g=None):
		self.e = e
		self.f = f
		self.g = g
		print('status: we are in the HandlerB constructor')
	@property
	def clean(self):
		out = dict(a=self.a,b=self.b)
		if self.c:
			out['c'] = self.c
		return out

# STEP 4: Attach to YAML
# We must prepare a YAML instance and attach our custom objects to it.

# automatically collect tags after defining yaml objects
tags_yaml_objects = [i for i in globals().keys() - keys_globals]
tags_yaml_objects = [globals()[tag] for tag in globals().keys() - keys_globals 
	if hasattr(globals().get(tag,None),'yaml_tag')]

# prepare the YAML instance
from ruamel.yaml import YAML,yaml_object
yaml = YAML(typ='rt')
yaml.width = 80

# build the trestle with the yaml tags
trestle,trestle_text = build_trestle(
	tags=tags_yaml_objects,
	yaml=yaml,get_text_completer=True)

### TEST DATA

test_A_input = """\
---
!my_doc
- a: 1
  b: 2
- e: 3
  f: 4
  g: 5
"""

test_A_out = """\
!my_doc
- !kind_a
  a: 1
  b: 2
- !kind_b
  e: 3
  f: 4
  g: 5
"""

### TEST SET

class TestTrestle(unittest.TestCase):
	"""
	Test the "trestle" pattern.
	"""
	def test_trestle_basic(self):
		# tests above are verbose so we suppress
		sys.stdout = io.StringIO()
		self.assertEqual(trestle_text(test_A_input),test_A_out)

### MAIN

if __name__ == '__main__':

	# a simple demonstration, via: python -i -m ortho.test_trestle
	print('status: starting with a single tag at the top of the document:\n')
	print(test_A_input)
	out = trestle_text(test_A_input)
	print('status: the resulting document is tagged:\n')
	print(out)
	print('status: to apply this method, use the build_trestle option to '
		'create a function that reads, modifies, and writes a YAML file '
		'on disk')
