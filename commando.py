# -*- coding: utf-8 -*-
"""
Declarative interface for argparse
"""
import argparse
from argparse import ArgumentParser
from collections import namedtuple
from pprint import pprint

# pylint: disable-msg=R0903,C0103,C0301

_hack = 0
import sys
def HACK():
  global _hack
  _hack += 1
  if _hack > 10:
    raise Exception("OVERFLOW HACK: %s" % _hack)
    sys.exit(1)

try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution('commando').version
except Exception:
    __version__ = 'unknown'

__all__ = ['command',
           'subcommand',
           'param',
           'version',
           'store',
           'true',
           'false',
           'append',
           'const',
           'append_const',
           'Application']

def add_arguments(parser, params):
    """
    Adds parameters to the parser
    """
    for parameter in params:
        parser.add_argument(*parameter.args, **parameter.kwargs)

class Commando(type):
    """
    Meta class that enables declarative command definitions
    """

    def __new__(mcs, name, bases, attrs):
        instance     = super(Commando, mcs).__new__(mcs, name, bases, attrs)
        main_command = None
        subcommands  = [ ]
        for name, member in attrs.iteritems():
            if hasattr(member, "command"):
                main_command = member
            elif hasattr(member, "subcommand"):
                subcommands.append(member)
        main_parser = None


        if main_command:
            main_parser = ArgumentParser(*main_command.command.args,
                                        **main_command.command.kwargs)
            add_arguments(main_parser, getattr(main_command, 'params', []))
            subparsers = None
            if len(subcommands):
                subparsers = main_parser.add_subparsers()
                for sub in subcommands:
                    parser = subparsers.add_parser(*sub.subcommand.args,
                                                  **sub.subcommand.kwargs)
                    parser.set_defaults(run=sub)
                    add_arguments(parser, getattr(sub, 'params', []))

        instance.__parser__ = main_parser
        instance.__main__ = main_command
        return instance

class Extent(type):
    """
    Meta class that enables declarative command definitions
    """

    def __new__(mcs, name, bases, attrs):
        instance     = super(Extent, mcs).__new__(mcs, name, bases, attrs)
        subcommands  = getattr(instance, '__subcommands__', [ ])
        main_command = None
        # scan for decorated items, and mark them up for the subclass to
        # process
        # attrs is all the properties of the class to be combined with all it's
        # sublcasses.  This spot in the metaclass is the easiest way to
        # traverse an object in this way.
        for name, member in attrs.iteritems():
            if hasattr(member, "command"):
                main_command = member
            elif hasattr(member, "subcommand"):
                subcommands.append(member)

        instance.__subcommands__ = subcommands
        instance.__parser__      = None
        instance.__main__        = main_command
        return instance

values = namedtuple('__meta_values', 'args, kwargs')

class metarator(object):
    """
    A generic decorator that tags the decorated method with
    the passed in arguments for meta classes to process them.
    """

    def __init__(self, *args, **kwargs):
        self.values = values._make((args, kwargs)) #pylint: disable-msg=W0212

    def metarate(self, func, name='values'):
        """
        Set the values object to the function object's namespace
        """
        setattr(func, 'commando', True)
        setattr(func, name, self.values)
        return func

    def __call__(self, func):
        return self.metarate(func)


class command(metarator):
    """
    Used to decorate the main entry point
    """

    def __call__(self, func):
        return self.metarate(func, name='command')


class subcommand(metarator):
    """
    Used to decorate the subcommands
    """

    def __call__(self, func):
        return self.metarate(func, name='subcommand')


class param(metarator):
    """
    Use this decorator instead of `ArgumentParser.add_argument`.
    """

    def __call__(self, func):
        func.params = func.params if hasattr(func, 'params') else []
        func.params.append(self.values)
        return func


class version(param):
    """
    Use this decorator for adding the version argument.
    """

    def __init__(self, *args, **kwargs):
        super(version, self).__init__(*args, action='version', **kwargs)

class store(param):
    """
    Use this decorator for adding the simple params that store data.
    """

    def __init__(self, *args, **kwargs):
        super(store, self).__init__(*args, action='store', **kwargs)

class true(param):
    """
    Use this decorator as a substitute for 'store_true' action.
    """

    def __init__(self, *args, **kwargs):
        super(true, self).__init__(*args, action='store_true', **kwargs)

class false(param):
    """
    Use this decorator as a substitute for 'store_false' action.
    """

    def __init__(self, *args, **kwargs):
        super(false, self).__init__(*args, action='store_false', **kwargs)

class const(param):
    """
    Use this decorator as a substitute for 'store_const' action.
    """

    def __init__(self, *args, **kwargs):
        super(const, self).__init__(*args, action='store_const', **kwargs)

class append(param):
    """
    Use this decorator as a substitute for 'append' action.
    """

    def __init__(self, *args, **kwargs):
        super(append, self).__init__(*args, action='append', **kwargs)

class append_const(param):
    """
    Use this decorator as a substitute for 'append_const' action.
    """

    def __init__(self, *args, **kwargs):
        super(append_const, self).__init__(*args, action='append_const', **kwargs)

class Shim(object):
  def __init__(self, func=None):
    if func is not None:
      self.main = func
  def __call__(self, app, params):
    self.app = app
    self.main(params)
  def main(self, params):
    "Unimplemented"
  def setup_parser(self):
    pass
    

class Base(Shim):
  def __init__(self, parser=None, func=None):
    super(Base, self).__init__(func=func)
    if parser is None:
      parser = ArgumentParser(*self.main.command.args,
                             **self.main.command.kwargs)
    self.__parser__ = parser
    self.setup_parser( )
  def setup_parser(self):
    main_command = self.main
    main_parser  = self.__parser__
    add_arguments(main_parser, getattr(main_command, 'params', [ ]))

class DecoratedShim(Base):
  """traverse a tree, looking for decorated callables
  
    A tree is an object hierarchy, where methods of the instance have properties.
    The properties set on function descriptors of the instance are most easily
    influenced using the decorators on a plain old object.
      
      * command - The decoration given by the command decorator.
        Represents a the default command callable for an entire new parser if
        no parser is present.  If a parser is present, call add_subparsers
        Use this as the main command for that entire parser.
          hint: should be passed 

      * subcommand - 
  """
  def __init__(self, parser=None, decor=None):
    HACK( )
    self.decor = decor
    func = decor
    if not callable(decor):
      main_command, subcommands = self.traverse(decor)
      group  = Subcommands(parser      =parser,
                           func        =main_command,
                           subcommands =subcommands)
      parser = group.__parser__
      func   = group
      super(DecoratedShim, self).__init__(parser=parser, func=func)

    else:
      pprint(['DECOR is a callable!', decor, vars(decor)])
      main_command, subcommands = self.traverse(decor)
      if main_command is None:
        main_command = decor
        func = decor
      pprint(['main, subs', main_command, subcommands])
      pprint(['parser', parser])
      if decor.commando and decor.branch:
        print "HAHAHA"
        branches = self.branch(parser)
        pprint(['branches', branches])

        #func   = group
      #super(DecoratedShim, self).__init__(parser=parser, func=func)
  

  def branch(self, parser):
    root     = self.decor
    branches = [ ]
    
    for name in getattr(root, 'branches', [ ]):
      member = getattr(root, name)
      main, subs = self.traverse(member)
      if main or subs:
        pprint(['branching? %s' % name, member, ]) # vars(member)])
        pprint(['found main', 'subs', main, subs])
        #branches.append(
        group  = Subcommands(parser      =parser,
                             func        =main,
                             subcommands =subs)
        branches.append(group)
    return branches
    
  def traverse(self, root):
    r = [ ]
    main_command = None
    subcommands  = [ ]
    for name in dir(root):
      member = getattr(root, name)
      if callable(member):
        if getattr(member, "commando", False):
          if hasattr(member, "command"):
            main_command = member
          elif hasattr(member, "subcommand"):
            subcommands.append(member)
    return (main_command, subcommands)

class Subcommands(Base):
  __subcommands__ = [ ]
  group           = None
  def __init__(self, parser=None, func=None, subcommands=None):
    if subcommands is not None:
      self.__subcommands__ = subcommands

    self.main = func
    super(Subcommands, self).__init__(parser=parser, func=func)

  def setup_parser(self):
    super(Subcommands, self).setup_parser( )
    main_parser = self.__parser__
    default = None

    sub_kwds = dict(default=default)
    # setup main command
    if self.main is not None:
      if not hasattr(self.main, 'subcommand'):
        name = self.main.func_name
        subcommand(name, help="my help command main")(self.main.im_func)
        sub_kwds['dest'] = argparse.SUPPRESS
        default = self.main.func_name
      else:
        pprint(['considering', self.main, vars(self.main)])
        pprint(['on behalf of ', self.__subcommands__])
        pprint(['for parser ', main_parser])
        if hasattr(self.main, 'subcommand'):
          default = self.main.subcommand.args[0]
          pprint(self.main.subcommand)
        else:
          default = self.main.im_func.subcommand.args[0]
      sub_kwds['default'] = default
      # add it as another subcommand
      self.__subcommands__.append(self.main)

    subparsers = main_parser.add_subparsers(**sub_kwds)

    for sub in self.__subcommands__:
      pprint(['add a new parser:', sub, vars(sub), sub.subcommand])
      parser = subparsers.add_parser(*sub.subcommand.args,
                                    **sub.subcommand.kwargs)
      if getattr(sub, 'branch', False):
        print "FOUND A BRANCH"
        pprint(['sub', sub, vars(sub), ])
                       #sub.im_func, vars(sub.im_func)])
        DecoratedShim(parser=parser, decor=sub)
        #setattr(sub.im_func, 'branch', False)
      else:
        parser.set_defaults(run=sub)
      add_arguments(parser, getattr(sub, 'params', []))

class BaseApp(object):
    def parse(self, argv):
        """
        Simple method that delegates to the ArgumentParser
        """
        return self.__parser__.parse_args(argv) #pylint: disable-msg=E1101

    def run(self, args=None):
        """
        Runs the main command or sub command based on user input
        """

        if not args:
            import sys
            args = self.parse(sys.argv[1:])

        if hasattr(args, 'run'):
            args.run(self, args)
        else:
            self.__main__(args)  #pylint: disable-msg=E1101

class TreeApp(BaseApp):
  def __init__(self, root=None):
    self.root = root

  def setup(self):
    # scan for decorated items, and mark them up for the subclass to
    # process
    self.__main__ = DecoratedShim(decor=self.root)
    self.__parser__ = self.__main__.__parser__

  def parse(self, argv):
    self.setup( )
    return super(TreeApp, self).parse(argv)

  def __main__(self, params):
    print "no"

class WeirdApp(BaseApp, Subcommands):
  __metaclass__ = Extent

class Application(BaseApp):
    """
    Barebones base class for command line applications.
    """
    __metaclass__ = Commando

#####
# EOF
