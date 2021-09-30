#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import os
import hashlib
import json

def meta_hasher(**metadata):
	"""
	Compute the metadata dictionary and hashcode for this run.
	We use the hashcodes to distinguish runs.
	"""
	# compute metadata once for this batch
	hashcode_this = hashlib.sha1(json.dumps(metadata,
		ensure_ascii=True,sort_keys=True,default=str
		).encode()).hexdigest()[:12]
	return metadata,hashcode_this
