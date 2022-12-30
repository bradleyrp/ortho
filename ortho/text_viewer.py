#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

import subprocess

def text_viewer(text,use_more=False):
	"""
	Pipe text to Vim for review.
	"""
	# note that "more" is not very compatible with cursesmenu
	kwargs = {
		"stdout": subprocess.PIPE,
		"stderr": subprocess.PIPE,}
	proc_echo = subprocess.Popen(['echo',text],stdin=subprocess.PIPE,**kwargs)
	if use_more:
		cmd = ['more','-']
	else:
		# we make an easy exit shortcut 'q' key
		# dev: make a vimrc flag to accept a custom configuration
		cmd = ['vim','-','+map q :q!<CR>','+set scrolloff=5','--not-a-term']
	proc = subprocess.Popen(cmd,stdin=proc_echo.stdout)
	proc.communicate()
