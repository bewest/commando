# -*- coding: utf-8 -*-
"""
Declarative interface for argparse
"""
from argparse import ArgumentParser
from collections import namedtuple
from pprint import pprint

# pylint: disable-msg=R0903,C0103,C0301

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
    print 'base'
    print 'main', self.main
    print 'func', func
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
    self.decor = decor
    func = decor
    if not callable(decor):
      print('decorating root tree')
      print(decor)
      main_command, subcommands = self.traverse(decor)
      pprint([main_command, subcommands])
      pprint(main_command.command)
      group     = Subcommands(parser      =parser,
                              func        =main_command,
                              subcommands =subcommands)
      parser    = group.__parser__
      #self.main = group.main
      print "decor main command group:", group
      super(DecoratedShim, self).__init__(parser=parser, func=group)
    else:
      super(DecoratedShim, self).__init__(func=func)

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

class DecoCommands(Base):
  def setup_parser(self):
    super(DecoCommands, self).setup_parser( )

class Subcommands(Base):
  __subcommands__ = [ ]
  group           = None
  def __init__(self, parser=None, func=None, subcommands=None):
    print "parser", parser
    print "subcommands init func", func
    print "subcommands func details", dir(func)
    print "subcommands init func.command", func.command
    if subcommands is not None:
      self.__subcommands__ = subcommands
    print 'FUNC', func
    self.main_command = func
    self.main = func
      

    super(Subcommands, self).__init__(parser=parser, func=func)

  def broke(self):
      if func is not None:
          root = Base(func=func, parser=parser)
          parser = root.__parser__
          print 'base, func', root, func, func.func_name
          group  = parser.add_subparsers(default=func.func_name)
          self.group = group
          parser = group.add_parser(func.func_name)
          parser.set_defaults(run=self)
          add_arguments(parser, getattr(root, 'params', []))


  def setup_parser(self):
    super(Subcommands, self).setup_parser( )
    main_parser = self.__parser__
    subparsers  = self.group
    default = None
    if self.main_command is not None:
      print "MAIN COMMAND", self.main_command
      if not hasattr(self.main_command, 'subcommand'):
        name = self.main_command.func_name
        #self.main_command.subcommand = values._make((name, dict(help="my main command")))
        subcommand(name, help="my main command")(self.main_command.im_func)
      default = self.main_command.func_name
    if subparsers is None:
      subparsers = main_parser.add_subparsers(default=default)

    # setup main command
    #root = Base(func=self.main_command, parser = )
    self.__subcommands__.append(self.main_command)
    for sub in self.__subcommands__:
      parser = subparsers.add_parser(*sub.subcommand.args,
                                    **sub.subcommand.kwargs)
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

