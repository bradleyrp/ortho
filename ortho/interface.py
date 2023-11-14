#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import subprocess
from .bash import command_check

def clipboard_copy(text,method='manual'):
	"""Wrap the clipboard copy mechanism."""
	# note that using this on a linux cluster requires ForwardX11, and you may
	#   also need to change the XQuartz setting to unselect "Update Pasteboard 
	#   when CLIPBOARD changes Disable this option if you want to use 
	#   clipboard, klipper, or any other Х11 clipboard manager."
	# we wrap this because pyperclip does not let you switch to the primary
	#   clipboard
	if method == 'pyperclip':
		import pyperclip as pc
		pc.copy(text)
	elif method == 'manual':
		if command_check('xclip'):
			command_copy = 'xclip -selection p'.split()
			proc = subprocess.Popen(command_copy,
				stdin=subprocess.PIPE)
			proc.communicate(text.encode('utf-8'))
		elif command_check('pbcopy'):
			command_copy = 'pbcopy'
			proc = subprocess.Popen(command_copy,env={'LANG':'en_US.UTF-8'},
				stdin=subprocess.PIPE)
			proc.communicate(text.encode('utf-8'))
		else: 
			raise Exception('cannot find xclip or pbcopy')
	else:
		raise Exception(f'invalid copy method {method}')
