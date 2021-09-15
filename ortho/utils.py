#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

def catalog(base,path=None):
	"""
	Traverse all paths in a nested dictionary. Returns a list of pairs: paths and values.
	Note that lists can be a child item; catalog does not expand the indices.
	"""
	if not path: path = []
	if isinstance(base,dict):
		for x in base.keys():
			local_path = path[:]+[x]
			for b in catalog(base[x],local_path): yield b
	else: yield path,base

