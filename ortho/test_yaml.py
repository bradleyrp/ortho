#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import os
import unittest
import yaml
import ruamel.yaml as yamlr
from .yaml import YAMLObjectOverride as YAMLObjectOrtho
from .yaml import collect_anchors
from .yaml import get_real_ruamel
from .yaml import YAMLAnchorInclude
from .yaml import YAMLIncludeBase
from .yaml import recursive_clean
from .yaml import decorate_clean_class
from .yaml_include import YAML as YAMLI

# dev: note no testing of YAMLIncludeBase yet, which requires files

class ExampleYaml:
	def __init__(self,arg,kwarg=None):
		self.arg = arg1
		self.kwarg = kwarg1

text_std = """\
!example_std 
hello: there
"""

text_ortho = """\
!example_ortho
hello: there
"""

text_ortho_missing = """\
!example_ortho
kwarg: 2
"""

text_ortho_correct = """\
!example_ortho
arg: 1
kwarg: 2
"""

text_ortho_null = """\
!example_ortho_null
hello: there
"""

text_has_anchors = """\
hello: &hi hello
"""

text_has_anchors_tags = """\
greeting: !cat &greet
  - hello
  - mary 
"""

text_anchor_base = """\
a: &b 1
"""

text_anchor_extend = """\
_dump: !include_anchors %(filename)s
c: *b
"""

text_inject_up = """\
name: Ryan
"""

text_inject_down = """\
!exclude _: !inject
person: *name
"""

text_include_up = """\
extrana:
  _: &name Ryan
"""

text_include_down = """\
!exclude includes: [!include %(filename)s]
name: *name
"""

text_include_down_simple = """\
a: b
z: !include %(filename)s
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

class ExampleOrthoNull(YAMLObjectOrtho):
	yaml_tag = '!example_ortho_null'

class OrthoYAMLOverrides(unittest.TestCase):
	"""Test YAML constructors, namely the overrides in ortho.YAMLObject."""
	def test_yaml_constructor_init(self):
		"""
		A normal YAML constructor ignores the __init__ method.
		"""
		loaded = yaml.load(text_std,Loader=yaml.Loader)
		self.assertEqual(loaded.__dict__,{'hello': 'there'})
	def test_ortho_init_fail_unexpected(self):
		"""
		The ortho version of YAMLObject uses __init__ and rejects unexpected
		arguments in the mapping node
		"""
		with self.assertRaisesRegex(TypeError,
			r'__init__\(\) got an unexpected keyword argument'):
			loaded = yaml.load(text_ortho,Loader=yaml.Loader)
	def test_ortho_init_fail_missing_expected(self):
		"""
		The ortho version of YAMLObject uses __init__ and expects incoming
		arguments by name.
		"""
		with self.assertRaisesRegex(TypeError,
			r'__init__\(\) missing \d+ required positional argument'):
			loaded = yaml.load(text_ortho_missing,Loader=yaml.Loader)
	def test_ortho_init_fail_null(self):
		"""
		The ortho version of YAMLObject requires an __init__ method.
		"""
		with self.assertRaisesRegex(TypeError,
			r'takes no arguments'):
			loaded = yaml.load(text_ortho_null,Loader=yaml.Loader)
	def test_ortho_init(self):
		"""
		The ortho version of YAMLObject uses __init__ verbatim and can 
		also run other code.
		"""
		loaded = yaml.load(text_ortho_correct,Loader=yaml.Loader)
		self.assertEqual(loaded.__dict__,{'arg':1,'kwarg':2,'novel':3})

class RuamelOrtho(unittest.TestCase):
	def setUp(self):
		self.yaml_parent = get_real_ruamel(parent=True)
		self.yaml = self.yaml_parent.YAML(typ='rt')
	def test_collect_anchors(self):
		"""
		Collect a dictionary of anchors from a YAML file.
		"""
		yaml_this = self.yaml
		loaded = yaml_this.load(text_has_anchors)
		index = collect_anchors(data=loaded)
		self.assertEqual(index,
			{'hi': 'hello'})
	def test_collect_anchors_tags(self):
		"""
		Collect a dictionary of anchors from a YAML file while preserving
		and not resolving tags. This is superceded by ortho.yaml_include.
		"""
		yaml_this = self.yaml
		loaded = yaml_this.load(text_has_anchors_tags)
		index = collect_anchors(data=loaded)
		self.assertEqual(index,
			{'greet':['hello','mary']})
	def DEPRECATED_test_yaml_anchor_include(self):
		"""
		Test the anchor include functionality.
		"""
		# dev: this is deprecated. see ortho.yaml_include and associated tests
		#   for a better method. in short, it was very challenging to inject
		#   the anchors from collect_anchors into a reader without using a 
		#   full-blown method for including other composers when we parse
		yaml_this = self.yaml
		yaml_this.register_class(YAMLAnchorInclude)
		import tempfile
		with tempfile.NamedTemporaryFile('w',delete=False) as tf:
			tf.write(text_anchor_base)
		loaded = yaml_this.load(text_anchor_extend%dict(
			filename=tf.name))
		os.remove(tf.name)
		self.assertEqual(loaded,
			{'a':1,'_dump':{'b':1},'c':1})
	def test_yaml_inject(self):
		"""
		Test a feature in which we inject a namespace into a YAML file.
		"""
		ns = {'name':'Ryan'}
		yaml = YAMLI(ns=ns)
		loaded = yaml.load(text_inject_down)
		self.assertEqual(loaded,{'person':ns['name']})
	def test_yaml_include(self):
		"""
		Test a YAML include feature.
		"""
		import tempfile
		with tempfile.NamedTemporaryFile('w',delete=False) as tf:
			tf.write(text_include_up)
		yaml = YAMLI()
		loaded = yaml.load(text_include_down%dict(
			filename=tf.name))
		os.remove(tf.name)
		self.assertEqual(loaded,{'name':'Ryan'})
	def test_yaml_include_basic(self):
		"""
		The YAMLIncludeBase class can perform a simple include-like 
		functionality but cannot preserve anchors, so ortho.yaml_include 
		is preferred instead.
		"""
		class YAMLIncludeNow(YAMLIncludeBase,YAMLObjectOrtho):
			yaml_tag = '!include'
		import tempfile
		with tempfile.NamedTemporaryFile('w',delete=False) as tf:
			tf.write(text_anchor_base)
		loaded = yaml.load(text_include_down_simple%dict(
			filename=tf.name),Loader=yaml.Loader)
		os.remove(tf.name)
		self.assertEqual(loaded,{'a':'b','z':{'a':1}})

class StandardYAMLTag:
	"""
	Example of a standard YAML tag, compatible with pyyaml and also
	ruamel.yaml and also able to be parsed by collect_anchors. 
	We use string concatenation as an example
	"""
	yaml_tag = '!cat'
	char = ' '
	def __init__(self,text):
		self.text = text
	@classmethod
	def from_yaml(cls,constructor,node):
		return cls(cls.char.join([i.value for i in node.value]))
	@classmethod
	def to_yaml(cls,representer,node):
		return representer.represent_scalar(cls.yaml_tag,node.text)
	@property
	def clean(self):
		return self.text

class StandardYAMLTagOrtho(YAMLObjectOrtho):
	yaml_tag = '!cat'
	char = ' '
	def __init__(self,*args):
		self.text = self.char.join(args)
	@property
	def clean(self):
		return self.text

class YAMLTalk(unittest.TestCase):
	"""
	These test cases handle conversion between YAML and dictionaries instead of
	class objects.
	"""
	def test_standard_ruamel(self):
		"""
		Standard yaml_tag method for ruamel.
		"""
		yaml_this = yamlr.YAML()
		# in ruamel we register classes to use yaml_tags
		yaml_this.register_class(StandardYAMLTag)
		loaded = yaml_this.load(text_has_anchors_tags)
		cleaned = recursive_clean(loaded)
		self.assertEqual(cleaned,
			{'greeting':'hello mary'})

	def test_standard_pyyaml(self):
		"""
		Standard yaml_tag method for pyyaml.
		"""
		# in pyyaml we subclass YAMLObject, but it is nice to use 
		#   YAMLObjectOrtho in this example because it allows logic in the
		#   constructor
		loaded = yaml.load(text_has_anchors_tags,Loader=yaml.Loader)
		cleaned = recursive_clean(loaded)
		self.assertEqual(cleaned,{'greeting':'hello mary'})
