#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

### MWE: a yaml doc that you can add to sytematically

import sys
import typing
import io
import unittest

import ortho
from ortho import Handler, YAMLDocumentBuilder

import ruamel
from ruamel.yaml import YAML,yaml_object

test_seq = """\
--- !mydoc
- !food
  name: sourdough
  raw: 100kcal energy, 30g serving
- name: eggs
  raw: 100kcal energy, 20g serving, 10g super
- name: eggs over easy
  foods:
    - eggs 100g
    - sourdough 60g # note extra salt
"""

test_dict = """\
--- !mydoc
sourdough: !food
  raw: 100kcal energy, 30g serving
eggs:
  raw: 100kcal energy, 20g serving, 10g super
eggs over easy:
  foods:
    - eggs 100g
    - sourdough 60g # note extra salt
"""

test_seq_built = """\
!mydoc
- !food
  name: sourdough
  raw: 100kcal energy, 30g serving
- !food
  raw: 100kcal energy, 20g serving, 10g super
  name: eggs
- !meal
  foods:
  - eggs 100g
  - sourdough 60g   # note extra salt
  name: eggs over easy
"""

test_dict_built = """\
!mydoc
sourdough: !food
  raw: 100kcal energy, 30g serving
eggs: !food
  raw: 100kcal energy, 20g serving, 10g super
  name:
eggs over easy: !meal
  foods:
  - eggs 100g
  - sourdough 60g   # note extra salt
  name:
"""

class MyBuilder(Handler):
	"""
	Build YAML objects based on keys.
	"""
	def food(self,*,raw,name=None):
		return Food(
			raw=raw,name=name)
	def meal(self,*,foods,name=None):
		return Meal(
			foods=foods,name=name)

# the handler requires us to use the solve property to return an object
builder_solved = lambda *args,**kwargs: MyBuilder(*args,**kwargs).solve

class MyDocument(YAMLDocumentBuilder): 
	yaml_tag = '!mydoc'
	# build objects from multiple dispatch on kwargs keys
	builder = builder_solved

class Food:
	yaml_tag = '!food'
	def __init__(self,*,raw,name=None):
		self.raw = raw
		self.name = name

class Meal:
	yaml_tag = '!meal'
	def __init__(self,*,foods,name=None):
		self.foods = foods
		self.name = name

class OrthoYAMLOverrides(unittest.TestCase):
	def test_yaml_document_builder(self):
		"""
		Test the YAMLDocumentBuilder.
		"""
		yaml = YAML(typ='rt')
		yaml.width = 80
		yaml.register_class(MyDocument)
		yaml.register_class(Food)
		yaml.register_class(Meal)
		for test_text,built_text in [
			(test_seq,test_seq_built),
			(test_dict,test_dict_built)]:
			doc = yaml.load(test_text)
			buffer = io.BytesIO()
			yaml.dump(doc,buffer)
			self.assertEqual(
				buffer.getvalue().decode().split('\n'),
				built_text.split('\n'))
