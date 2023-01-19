#!/usr/bin/env python
# vim: noet:ts=4:sts=4:sw=4

"""
Interactive execution, reexecution, debugging, and development tools.
"""

from __future__ import print_function
import sys,re
import ast
import readline
import rlcompleter
import traceback
import code
import pprint

def say(text,*flags):
	"""Colorize the text."""
	# three-digit codes. first is style (0,2 are regular, italics 3, bold 1)
	colors = {
		'gray':(0,37,48),
		'cyan_black':(1,36,40),
		'red_black':(1,31,40),
		'black_gray':(0,37,40),
		'white_black':(1,37,40),
		'mag_gray':(0,35,47)}
	# no colors if we are logging to a text file because nobody wants all that
	#   unicode in a log
	if flags and hasattr(sys.stdout,'isatty') and sys.stdout.isatty() is True:
		if any(f for f in flags if f not in colors):
			raise Exception('cannot find a color %s. try one of %s'%(
				str(flags),colors.keys()))
		for f in flags[::-1]:
			style,fg,bg = colors[f]
			text = '\x1b[%sm%s\x1b[0m'%(';'.join(
				[str(style),str(fg),str(bg)]),text)
	return text

def tracebacker_base(exc_type,exc_obj,exc_tb,debug=False):
	"""Base handler `tracebacker`."""
	tag = say('[TRACEBACK]','gray')
	tracetext = tag+' '+re.sub(r'\n','\n%s'%tag,
		str(''.join(traceback.format_tb(exc_tb)).strip()))
	if not debug:
		print(say(tracetext))
		print(say('[ERROR]','red_black')+' '+say('%s'%exc_obj,'cyan_black'))
	else:
		try: import ipdb as pdb_this
		except:
			print('note','entering debug mode but '
				'cannot find ipdb so we are using pdb')
			import pdb as pdb_this
		print(say(tracetext))
		print(say('[ERROR]','red_black')+' '+say('%s'%exc_obj,'cyan_black'))
		print(say('[DEBUG] entering the debugger','mag_gray'))
		pdb_this.pm()

def tracebacker(*args,**kwargs):
	"""Standard traceback handling for easy-to-read error messages."""
	debug = kwargs.pop('debug',False)
	if kwargs:
		raise Exception('unprocessed kwargs %s'%kwargs)
	# note that handling interrupts prevents normal traceback
	if len(args)==1:
		exc_type,exc_obj,exc_tb = sys.exc_info()
		tracebacker_base(exc_type,exc_obj,exc_tb,debug=debug)
	elif len(args)==3: tracebacker_base(*args,debug=debug)
	else: raise Exception(
		'tracebacker expects either one or three arguments but got %d'%
		len(args))

def debugger(*args):
	"""Run the tracebacker with interactive debugging if possible."""
	debug = not (hasattr(sys, 'ps1') or not sys.stderr.isatty())
	if args[0]==KeyboardInterrupt:
		print()
		print('status','received KeyboardInterrupt')
		debug = False
	return tracebacker(*args,debug=debug)

def rename_attribute(object_, deadname, name):
	"""Rename an attribute. Essential for flexible names for `ReExec`."""
	setattr(object_, name, getattr(object_, deadname))
	delattr(object_, deadname)

class ReExec:
	"""
	Supervise interactive execution. This class provides "commands" inside the
	terminal to iteratively reexecute pieces of code without expensive loading
	operations. This function is part of a simple tool for streamlining
	development with minimal dependencies specifically on systems where it can
	be tedious to install lots of different tools.
	"""
	me = None
	# naming conventions for commands in the interactive development environment
	_names = {
		# reimport all modules
		# critical note: if you use `reimport`, you must also use `go` in order
		#   to actually reuse the code. we are not sure why this happens, 
		#   however, `reimport;go` with `pdb.set_trace` in the reimported 
		#   modules works perfectly and is a major help during development
		# dev: document the critical note above and investigate the root cause
		'reload':'reimport',
		# the "do" function runs the entire script again, however this can be
		#   very useful when using the `if 'variable' in globals():` method
		#   to avoid rerunning blocks of code in a script. the `redo` function
		#   is somewhat more tempermental because it attempts to identify novel
		#   code in your script using the abstract syntax trees
		'do':'go',
		# the redo function will compute changed parts of the script. we name
		#   it changes to emphasize that you are rerunning the changes
		'redo':'changes',}
	class CodeChunk:
		def __init__(self,code,index=None):
			self.i = index
			if isinstance(code,str): self.this = ast.parse(code)
			else: self.this = code
		def dump(self): return ast.dump(self.this)
		def __eq__(self,other):
			return self.dump==other.dump
		def __hash__(self): return hash(self.dump)
		def __repr__(self): return self.dump
	def __init__(self,file,namespace=None):
		self.namespace = {} if namespace is None else namespace
		self.namespace[self._names['redo']] = self.redo
		ReExec.me = self
		self.text = None
		self.file = file
		self.get_text()
		self.get_changes()
	def get_text(self):
		self.text_before = self.text
		with open(self.file) as fp: self.text = fp.read()
	def get_changes(self):
		if not self.text_before: return
		tree_before = ast.parse(self.text_before)
		tree = ast.parse(self.text)
		if ast.dump(tree)==ast.dump(tree_before):
			print('status','no changes to the script')
		else:
			print('status','executing changes to %s'%self.file)
			# identify changed nodes in the tree and execute
			# note that this feature reruns any changed child of script parent
			# dev: track line numbers and report to the user?
			tree_before,tree = [[self.CodeChunk(i,index=ii) for ii,i in
				enumerate(ast.iter_child_nodes(ast.parse(t)))]
				for t in [self.text_before,self.text]]
			intersect = set.intersection(set(tree),set(tree_before))
			novel = list(set.difference(set(tree),intersect))
			novel_linenos = set([i.this.lineno for i in novel])

			class CodeSurgery(ast.NodeTransformer):
				def visit(self, node):
					if (hasattr(node,'lineno') and
						node.lineno not in novel_linenos):
						return ast.parse('last_lineno = %d'%node.lineno).body[0]
					else: return ast.NodeTransformer.generic_visit(self,node)

			code_ready = ast.fix_missing_locations(
				CodeSurgery().visit(ast.parse(self.text)))
			# run the remainder
			out = self.namespace
			# dev: exec to eval for python <2.7.15. deprecated? unsafe?
			eval(compile(code_ready,filename='<ast>',mode='exec'),out,out)

	def redo(self):
		"""
		A function which reruns the changed parts of a script.
		Exported to an interactive script.
		"""
		self.get_text()
		self.get_changes()
	def do(self):
		print('status rerunning the script')
		out = self.namespace
		self.get_text()
		# canny way to handle exceptions below. all exceptions visit this
		try: exec(self.text,out,out)
		except Exception as e: tracebacker(e)
	def reload(self):
		global preloaded_mods
		preloaded_names = [i.__name__ for i in preloaded_mods]
		# dev: hardcoded excludes due to numpy errors
		# numpy does not like to be reimported. when we use `reimport;go` inside
		#   of an interactive session, we see "ValueError: Only callable can be 
		#   used as callback" coming from `numpy/core/_ufunc_config.py` whenever
		#   we try to look at numpy objects in the debugger. we prevent
		#   reimports here
		excludes = ['^numpy']
		import importlib
		mods_loaded = list(sys.modules.values())
		failures = []
		reloaded = []
		skips = []
		for module in mods_loaded:
			if module.__name__ in preloaded_names: 
				skips.append(module.__name__)
				continue
			# dev: see above. temporarily removed
			if any(re.match(regex,module.__name__) 
				for regex in excludes):
				continue
			try:
				importlib.reload(module)
				reloaded.append(module.__name__)
			except: 
				failures.append(module.__name__)
		if failures:
			print('warning','failed to reload: '+', '.join(failures))

def iteratively_execute():
	"""
	Entry point for iterative reexecution.
	Run this function from a script to enter iterative reexecution, a simple
	development mode.
	"""
	import __main__
	ie = ReExec(file=__main__.__file__)
	rename_attribute(ie,'do',ie._names['do'])
	rename_attribute(ie,'redo',ie._names['redo'])
	rename_attribute(ie,'reload',ie._names['reload'])
	__main__.__dict__[ie._names['do']] = ie.do
	__main__.__dict__[ie._names['redo']] = ie.redo
	__main__.__dict__[ie._names['reload']] = ie.reload
	__main__.ie = ie

def interact(script='dev.py',hooks=None,**kwargs):
	"""
	Run a script interactively.
	This function call exeuctes a script in a
	development mode which specifically provides users with commands (`go`,
	`reload`, `repeat`) which streamline development of complex scripts that
	require lots of calculation. This effectively takes the place of a debugger,
	however it provides a more native coding experience.

	dev: start with an error and go nowhere
		a fatal flaw here is that running a script with an error in it on the 
		first execution then you cannot rerun things because you get the
		auto-debugger. in fact the auto-debugger prevents you from continuing
		to run anything, so errors are fatal before you complete one execution
	dev: when we add a pdb.set_trace to a reimport library we cannot run 
		commands inside the trace:
			ValueError: Only callable can be used as callback
		this means we cannot easily debug and return to interact
	"""
	module_host = kwargs.get('module_host',None)
	onward_kwargs = kwargs.get('onward',{})
	# save preloaded modules
	from sys import modules
	global preloaded_mods
	preloaded_mods = set([i for i in modules.values()])
	#! 	if not module_host or i.__name__!=module_host])

	coda = kwargs.pop('coda',None)
	# allow subclassing of ReExec
	reexec_class = kwargs.pop('reexec_class',ReExec)
	# previous method: os.system('python -i %s'%(script))
	out = globals()
	# allow onward args to be added here
	# dev: document this use-case from atgizmo.core.thick.cli
	out.update(**onward_kwargs)
	# allow for flexible command names in the terminal
	for key in ['do','redo','reload']:
		if key in kwargs:
			reexec_class._names[key] = kwargs[key]
	ie = reexec_class(file=script,namespace=out)
	sys.ps1 = ">>> "
	if hooks:
		if not isinstance(hooks,tuple):
			raise Exception('hooks must be a tuple')
		# hooks are applied in order and transform the outgoing dictionary
		# kwargs go through the hook fcuntion
		for hook in hooks:
			if not callable(hook):
				raise Exception('hooks must be callable: %s'%hook)
			hook(out,**kwargs)
	# nb: this is the site of a previous "coda" functionality which allowed one
	#   to execute a piece of code after each reexecution. this made the analogy
	#   between the "iterative reexeuction" method and proper debugging into
	#   one that is symmetric, simulating the act of stepping through code while
	#   still retaining the native coding experience
	out['__name__'] = '__main__'
	# dev: run the code once without main in case there is an error in main,
	#   then start the interactive session and allow an exception in main to
	#   continue inside the debugger. this would eliminate a case where an 
	#   exception in __main__ prevents interactive sessions altogether
	# let the script know we are ortho in case that is useful when building a
	#   script that could run with regular CLI arguments or with hardcoded
	#   tests during development
	out['___is_ortho'] = True
	# compatible version of execfile
	# dev: exec to eval for python <2.7.15. see note above
	# dev: the following cannot encounter exceptions or we exit. this means that
	#   when you start an interact session, the code must be basically perfect
	eval(compile(open(script).read(),filename=script,mode='exec'),out,out)
	# prepare the interactive session
	import code
	class InteractiveCommand:
		"""
		Run functions from the repr hence without parentheses.
		Useful for reeexecution commands.
		"""
		def __init__(self,func,name,prelim=None):
			self.func,self.name = func,name
			self.prelim = prelim
		def __repr__(self):
			# briefly considered doing this with @property but this works fine
			# currently the prelim feature is deprecated by a subclassed ReExec
			#   but we retain it here as an option
			if self.prelim:
				# dev: exec to eval for python <2.7.15. see note above
				eval(compile(self.prelim,'<string>','exec'),out,out)
			self.func()
			# return empty string but we always get a newline
			return ''
	# apply extra functions if we subclass ReExec to add extra commands
	if kwargs.get('commands',[]):
		collide = [i for i in kwargs['commands']
			if i in reexec_class._names.keys()]
		if any(collide):
			# dev: if you subclass one of the functions in the parent, then we
			#   get a name collision that prevents the function from executing
			#   from the repr
			raise Exception('cannot include commands with these names '
				'in a subclass of ReExec: %s'%collide)
		for cmd in kwargs['commands']:
			locals()[cmd] = InteractiveCommand(
				prelim=kwargs.get('do_prelim',None),
				func=getattr(ie,cmd),name=cmd)
	# standard interact gets do and redo
	else:
		out.update(
			# override functions so they can be invoked without parentheses
			do = InteractiveCommand(func=ie.do,
				name=reexec_class._names['do'],
				# code to run before reexecuting a script from the top with do
				prelim=kwargs.get('do_prelim',None)),
			redo = InteractiveCommand(func=ie.redo,
				name=reexec_class._names['redo']),
			reload = InteractiveCommand(func=ie.reload,
				name=reexec_class._names['reload']),)
		#! issue: the following is overwriting key,val so we are testing
		for key,val in reexec_class._names.items():
			out[val] = out.pop(key)
	# consolidate, add tab completion
	vars = globals()
	# filter out the "key" and "val" keys because they leak into the namespace
	vars.update(dict([(i,j) for i,j in locals().items() if i not in [
		'key','val','onward_kwargs']]))
	vars.update(**vars.pop('out'))
	readline.set_completer(rlcompleter.Completer(vars).complete)
	readline.parse_and_bind("tab: complete")
	# interact
	msg = kwargs.get('msg','(interactive mode)')
	code.interact(local=vars,banner=msg)

def debugger():
	"""Automatic debugger. Add this to an exception to debug on errors."""
	# via https://stackoverflow.com/a/242514/3313859
	type, value, tb = sys.exc_info()
	traceback.print_exc()
	last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
	frame = last_frame().tb_frame
	ns = dict(frame.f_globals)
	ns.update(frame.f_locals)
	# include tab completion here
	readline.set_completer(rlcompleter.Completer(ns).complete)
	# MacOS moved from GNU readline to libedit for license reasons
	#   however this can be solved with the alternate parse and bind
	#   below, which is added here for completeness. this needs tested 
	#   on linux. see helpful comment:
	#     https://github.com/Homebrew/homebrew-core/pull/\
	#       118098#issuecomment-1351499727
	readline.parse_and_bind("tab: complete")
	readline.parse_and_bind("bind ^I rl_complete")
	# let the user know they are debugging
	msg = "(auto debug in place)"
	code.interact(local=ns,banner=msg)

def interact_local(ns=None,msg=None):
	"""
	Start an interactive session in a function.
	Be sure to pass along the namespace.
	"""
	if not ns:
		raise Exception('please send locals to the "ns" (namespace) '
			'argument of interact_local')
	# include tab completion here
	readline.set_completer(rlcompleter.Completer(ns).complete)
	readline.parse_and_bind("tab: complete")
	# let the user know they are debugging
	msg = "(interact)" if msg == None else msg
	code.interact(local=ns,banner=msg)

def debugger_click(func,with_ctx=False):
	"""
	Decorator which sends the user to an interactive session whenever an 
	exception is encountered as long as the click context which is sent as the
	first argument includes a DEBUG boolean.
	"""
	def wrapper(ctx,*args,**kwargs):
		"""
		Wrap a CLI function with the debugger so that a flag can trigger 
		in-place interactive debugging.
		"""
		# run the function
		try:
			if with_ctx: result = func(ctx,*args,**kwargs)
			# dev: when doing a traceback, indicate that "string" means we are
			#   executing a script interactively for clarity
			else: result = func(*args,**kwargs)
		# option to use the debugger if we have ortho
		except:
			detail = pprint.pformat(dict(args=args,kwargs=kwargs))
			print(f'debugging call to {func.__name__}: {detail}')
			if ctx.obj['DEBUG']:
				debugger()
			else: raise
		else: return result
	wrapper.__name__ = func.__name__
	wrapper.__doc__ = func.__doc__
	return wrapper
