#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import functools

def compose(*functions):
	"""Generic function composition."""
	def composer(f,g):
		return lambda x: f(g(x))
	return functools.reduce(composer,functions,lambda x: x)
