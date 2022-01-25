#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Diagnostic tools for monitoring execution.
"""

import timeit
class linetime:
	"""Measuring timing for a block of code."""
	#! via https://stackoverflow.com/a/52749808
	def __init__(self,name=None,factor=None):
		self.name = name if name else ''
		self.factor = factor
	def __enter__(self):
		self.start = timeit.default_timer()
	def __exit__(self,exc_type,exc_value,traceback):
		self.took = (timeit.default_timer()-self.start)
		print('[TIME] block %s took: %.2fs'%(self.name,self.took)+(
			' with scale-up: %.2f'%(self.took*self.factor)
			if self.factor else ''))
