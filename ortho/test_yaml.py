#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import unittest
import yaml
from .yaml import YAMLObject as YAMLObjectOrtho

class ExampleYaml:
	def __init__(self,arg,kwarg=None):
		self.arg = arg1
		self.kwarg = kwarg1

text_std = """
!example_std 
hello: there
"""

text_ortho = """
!example_ortho
hello: there
"""

text_ortho_missing = """
!example_ortho
kwarg: 2
"""

text_ortho_correct = """
!example_ortho
arg: 1
kwarg: 2
"""

class ExampleStd(yaml.YAMLObject):
	yaml_tag = '!example_std'
	def __init__(self,arg,kwarg=None):
		self.arg = arg
		self.kwarg = kwarg

class ExampleOrtho(YAMLObjectOrtho):
	yaml_tag = '!example_ortho'
	def __init__(self,arg,kwarg=None):
		self.arg = arg
		self.kwarg = kwarg
		self.novel = 3

class TestHandler(unittest.TestCase):
	"""Test YAML constructors."""
	def test_yaml_constructor_init(self):
		"""
		A normal YAML constructor ignores the __init__ method.
		"""
		loaded = yaml.load(text_std,Loader=yaml.Loader)
		self.assertEqual(loaded.__dict__,{'hello': 'there'})
	def test_ortho_init_fail(self):
		"""
		The ortho version of YAMLObject uses __init__ and rejects incorrect
		arguments in the mapping node.
		"""
		with self.assertRaisesRegex(TypeError,
			r'__init__\(\) got an unexpected keyword argument'):
			loaded = yaml.load(text_ortho,Loader=yaml.Loader)
		with self.assertRaisesRegex(TypeError,
			r'__init__\(\) missing'):
			loaded = yaml.load(text_ortho_missing,Loader=yaml.Loader)
	def test_ortho_init(self):
		"""
		The ortho version of YAMLObject uses __init__ verbatim and can 
		also run other code.
		"""
		loaded = yaml.load(text_ortho_correct,Loader=yaml.Loader)
		self.assertEqual(loaded.__dict__,{'arg':1,'kwarg':2,'novel':3})
