#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

__all__ = [
	'version',
	'print_function','ortho_print',
	'ortho_interact',]

from ._version import version
from .reexec import interact as ortho_interact
from .logs import stylized_print as ortho_print
