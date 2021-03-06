#!/usr/bin/env/python3
"""An inheritable command line interface generator inspired by cmd.py."""
from inspect import getmembers, ismethod, signature
from enum import Enum
import readline
from math import floor
import os
import pprint


# TODO: replace input entirely with something that handles "ESC" characters and returns None.
# TODO: enable tab completion for string input with limited scope of opions. (Custom enums?)
# TODO: enable tab completion for help
# TODO: test negative number int input
# TODO: implement completion for setter @property decorators.

def cli_method(func):
    """Decorator to register method as available to the CLI."""
    func.is_cli_method = True
    #setattr(func, 'is_cli_method', True)
    return func

class UserInputError(Exception):
    """Base exception for user inputting something incorrectly."""
    pass


def print_columnized_list(my_list, column_width=None):
    """Prints a list as a set of columns, maximizing screen space."""
    if column_width is None:
        _, column_width = map(int, os.popen('stty size', 'r').read().split())
    max_string_len = max(map(len, my_list)) + 1 # add 1 for minimum whitespace.
    column_count = floor(column_width/max_string_len)
    list_iter = iter(my_list)
    list_item = next(list_iter)
    try:
        while True:
            for i in range(column_count):
                # Print item; fill the remaining column block with whitespace.
                print(f"{list_item:<{max_string_len}}", end="")
                list_item = next(list_iter)
            print()
    except StopIteration:
        pass # Done printing.


class Inpromptu(object):
    """The Introspective Prompt
    A framework for inferring line-oriented command prompts.

    These are often useful for providing a bare-bones interface to various
    real-world devices or other software tools.

    This class should be inheritted by the class that requires an interface.
    You may expose methods by decorating them with the cli_method decorator.

    """
    prompt = ">>> "
    complete_key = 'tab'
    DELIM = ' '


    def __init__(self):
        """collect functions."""
        # Containers for methods and their signatures.
        # Methods decorated with @property become property objects which can
        # contain up to 3 methods: fget, fset, and fdel.
        # From the user perspective, fget and fset have the same name, but
        # different signature, so we hold onto all properties so that we can
        # invoke fgets separately.
        self.cli_methods, self.property_getters = self._get_cli_methods()
        self.callables = set({**self.cli_methods, **self.property_getters}.keys())
        self.cli_method_definitions = self._get_cli_method_definitions()
        #import pprint
        #pprint.pprint(self.cli_method_definitions)
        #pprint.pprint(self.cli_methods)
        #pprint.pprint(self.property_getters)

        # In-function completions for calling input() within a fn.
        # Note that this variable must be cleared when finished with it.
        self.completions = None
        self.prompt = self.__class__.prompt


    def _get_cli_methods(self):
        cli_methods = {}
        property_getters = {}

        # Collect all methods that have the is_cli_method as an attribute
        #cli_methods = {m[0]:m[1] for m in getmembers(self)
        #                if ismethod(getattr(self, m[0]))
        #                and hasattr(m[1], 'is_cli_method')}

        # Workaround because getmembers does not get functions decorated with @property
        # https://stackoverflow.com/questions/3681272/can-i-get-a-reference-to-a-python-property
        def get_dict_attr(obj, attr):
            for obj in [obj] + obj.__class__.mro():
                if attr in obj.__dict__:
                    return obj.__dict__[attr]
            raise AttributeError

        for name in dir(self):
            #print(name)
            value = get_dict_attr(self, name)
            # Special case properties, which may be tied to 2 relevant methods.
            if isinstance(value, property):
                if hasattr(value.fset, 'is_cli_method'):
                    cli_methods[name] = value.fset
                if hasattr(value.fget, 'is_cli_method'):
                    # Store the getter elsewhere to prevent name clash
                    property_getters[name] = value.fget
                continue
            if isinstance(value, classmethod):
                value = value.__func__
            if hasattr(value, 'is_cli_method'):
                cli_methods[name] = value

        return cli_methods, property_getters


    def _get_cli_method_definitions(self):
        """Build method definitions.

        Returns:
            Dictionary of method names mapped to their definitions.
        """
        definitions = {}

        for method_name, method in self.cli_methods.items():
            parameters = {}
            param_order = []
            sig = signature(method)

            # FIXME: how does this code handle functions wrapped in decorators??
            # Collapse to the function any wrapped functions.
            # This works only for function decorator wrappers using
            # functools.wraps to do the wrapping
            #while hasattr(method, "__wrapped__"):
            #    method = method.__wrapped__

            for parameter_name in sig.parameters:
                param_order.append(parameter_name)
                parameter = {}
                parameter_type = None
                parameter_sig = sig.parameters[parameter_name]
                if parameter_sig.annotation is not parameter_sig.empty:
                    parameter_type = parameter_sig.annotation
                parameter['type'] = parameter_type if parameter_type is not None else None


                # Enforce type hinting for all decoorated methods.
                if parameter['type'] is None and parameter_name not in ['self', 'cls']:
                    raise SyntaxError(f"Error: {method_name} must be type hinted. \
                                        Cannot infer type for arg: {parameter_name}.")

                # Check for defaults.
                if parameter_sig.default is not parameter_sig.empty:
                    parameter["default"] = parameter_sig.default
                elif parameter_name == 'self':
                    parameter["default"] = self
                elif parameter_name == 'cls':
                    parameter["default"] = self.__class__

                # Check for Enum types.
                if parameter_type is not None and issubclass(parameter_type, Enum):
                    parameter["type"] = "Enum"
                    parameter["options"] = list(parameter_type.__members__.keys())

                parameters[parameter_name] = parameter

            definitions[method_name] = {
                "param_order": param_order,
                "parameters": parameters,
                "doc": method.__doc__
            }

        return definitions


    def _match_display_hook(self, substitution, matches, longest_match_length):
        """Display custom response when invoking tab completion."""
        # Warning: exceptions raised in this fn are not catchable.
        # This issue is connected to the readline implementation.
        line = readline.get_line_buffer() # entire line of entered text so far.
        cmd_with_args = line.split()
        print()
        # Render explicitly specified completions in the original order:
        if self.completions:
            # Matches arrive alphebatized. Specify order according to original.
            matches = sorted(matches, key=lambda x: self.completions.index(x))
            #for match in matches:
            #    print(match, end=" ")
            print_columnized_list(matches)
        # Render Function Name:
        elif len(cmd_with_args) == 0 or \
            (len(cmd_with_args) == 1 and line[-1] is not self.__class__.DELIM):
            # Render function name matches.
            #for match in matches:
            #    print(match, end=" ")
            print_columnized_list(matches)
        # Render Function Args:
        else:
            param_order = [f"{x}=" for x in self.cli_method_definitions[self.func_name]['param_order']]
            # matches arrive alphebatized. Specify order according to original.
            matches = sorted(matches, key=lambda x: param_order.index(x))
            # Render argument matches with type.
            # Track argument index such that we only display valid options.
            for arg_completion in matches:
                arg = arg_completion.split("=")[0]
                arg_type = self.cli_method_definitions[self.func_name]['parameters'][arg]['type']
                print(f"{arg}=<{arg_type.__name__}>", end=" ")
        print()
        print(self.prompt, readline.get_line_buffer(), sep='', end='', flush=True)


    def input(self, prompt=None):
        """Wrapper for prompt function.
        Enables tab-completion while preserving full prompt prefix."""
        # Override the prompt if a custom prompt is requested.
        if prompt:
            self.prompt = prompt
        else:
            self.prompt = self.__class__.prompt
        return input(self.prompt)


    def complete(self, text, state, *args, **kwargs):
        """function invoked for completing partially-entered text.
        Formatted according to readline's set_completer spec:
        https://docs.python.org/3/library/readline.html#completion

        This fn is invoked upon pressing the TAB key.

        Note: this fn gets called by readline really weirdly.
        This fn gets called repeatedly with increasing values of state until
        the fn returns None.
        """
        # Warning: exceptions raised in this fn are not catchable.

        text = text.lstrip() # what we are matching against
        line = readline.get_line_buffer() # The whole line.
        cmd_with_args = line.split()


        # Take custom overrides if any are defined.
        if self.completions:
            return [c for c in self.completions if c.startswith(text)][state]

        # Complete the fn name.
        if len(cmd_with_args) == 0 or \
            (len(cmd_with_args) == 1 and line[-1] is not self.__class__.DELIM):
            # Return matches but omit match if it is fully-typed.
            results = [fn for fn in self.callables if fn.startswith(text) and fn != text]
            return results[state]

        # Complete the fn params.
        self.func_name = cmd_with_args[0]
        param_signature = cmd_with_args[1:]
        self.func_params = self.cli_method_definitions[self.func_name]['param_order']
        if self.func_params[0] in ['self', 'cls']:
            self.func_params = self.func_params[1:]

        # First filter out already-entered positional arguments.
        # Abort upon first keyword.
        first_kwarg_found = False
        first_kwarg_index = 0
        for entry_index, text_block in enumerate(param_signature):
            kwarg = None
            # Check if text entry is a fully-entered kwarg.
            for param_order_index, param_name in enumerate(self.func_params):
                completion = f"{param_name}="
                #print(f"text block: {text_block} | completion {completion}")
                if text_block.startswith(completion):
                    kwarg = param_name
                    if not first_kwarg_found:
                        first_kwarg_found = True
                        first_kwarg_index = entry_index
                    break
            if first_kwarg_found:
                break
            # Don't remove the last element if it is not fully entered.
            if text_block == param_signature[-1] and line[-1] is not self.__class__.DELIM:
                break
            first_kwarg_index += 1

        self.func_params = self.func_params[first_kwarg_index:]

        #print(f"found kwarg: {first_kwarg_found} | at index {first_kwarg_index}")
        #print(f"unfiltered params: {self.func_params}")

        # Then generate completion list from remaining possible params.
        func_param_completions = []
        for param_order_index, param_name in enumerate(self.func_params):
            completion = f"{param_name}="
            # No space case: arg is fully typed but missing a space
            if line[-1] is not self.__class__.DELIM and param_signature[-1].startswith(completion):
                return None
            # Filter out already-populated argument options by name and position.
            skip = False
            for text_block in param_signature:
                if text_block.startswith(completion):
                    skip = True
                    break
            # regular check
            if completion.startswith(text) and not skip:
                func_param_completions.append(completion)

        return func_param_completions[state]


    def cmdloop(self, loop=True):
        """Repeatedly issue a prompt, accept input, and dispatch to action
        methods, passing them the line remainder as argument.
        """

        readline.set_completer(self.complete)
        readline.set_completion_display_matches_hook(self._match_display_hook)
        readline.parse_and_bind(f"{self.__class__.complete_key}: complete")
        while True:
            try:
                line = self.input()
                if line == "":
                    continue
                ## Extract fn and args.
                fn_name, *arg_blocks = line.split()
                kwargs = {}

                no_more_args = False # indicates end of positional args in fn signature

                # Check if fn even exists.
                if fn_name not in self.callables:
                    raise UserInputError(f"Error: {fn_name} is not a valid command.")

                # Shortcut for @property getters which have no parameters and
                # whose function pointers are stored elsewhere to prevent name
                # name clashing with their setters.
                if len(arg_blocks) == 0 and fn_name in self.property_getters:
                    return_val = None
                    try:
                        return_val = self.property_getters[fn_name](self)
                    except Exception as e:
                        print(f"{fn_name} raised an excecption while being executed.")
                        print(e)
                    # Reset any completions set during this function.
                    finally:
                        self.completions = None
                    if return_val is not None:
                        pprint.pprint(return_val)
                    if not loop:
                        return
                    else:
                        continue

                param_count = len(self.cli_method_definitions[fn_name]['param_order'])
                param_order = self.cli_method_definitions[fn_name]['param_order']
                # Remove self or cls from param count and arg list.
                if self.cli_method_definitions[fn_name]['param_order'][0] in ['self', 'cls']:
                    param_count -= 1
                    param_order = param_order[1:]
                # Ensure required arg count is met.
                if len(arg_blocks) > param_count:
                    raise UserInputError("Error: too many positional arguments.")

                # Collect args and kwargs, enforcing args before kwargs.
                for arg_index, arg_block in enumerate(arg_blocks):
                    # Assume keyword arg is specified by key/value pair split by '='
                    try:
                        arg_name, val_str = arg_block.split("=")
                        no_more_args = True
                    # Otherwise: positional arg. Enforce parameter order.
                    except (ValueError, AttributeError):
                        # Enforce that positional args come before kwargs.
                        if no_more_args:
                            raise UserInputError(
                                "Error: all positional arguments must be "
                                 "specified before any keyword arguments.")
                        arg_name = param_order[arg_index]
                        val_str = arg_block
                    val = self.cli_method_definitions[fn_name]['parameters'][arg_name]['type'](val_str)
                    kwargs[arg_name] = val

                # Populate missing params with their defaults.
                # Raise error if are required param is missing.
                kwarg_settings = self.cli_method_definitions[fn_name]['parameters']
                missing_kwargs = []
                for key, val in kwarg_settings.items():
                    if key not in kwargs:
                        if 'default' in kwarg_settings[key]:
                            kwargs[key] = kwarg_settings[key]['default']
                        else:
                            missing_kwargs.append(key)
                if missing_kwargs:
                    raise UserInputError(
                        f"Error: the following required parameters are "
                        f"missing: {missing_kwargs}")

                # Invoke the fn.
                return_val = None
                try:
                    return_val = self.cli_methods[fn_name](**kwargs)
                except Exception as e:
                    print(f"{fn_name} raised an excecption while being executed.")
                    print(e)
                # Reset any completions set during this function.
                finally:
                    self.completions = None
                if return_val is not None:
                    pprint.pprint(return_val)
            except (EOFError, UserInputError) as e:
                print(e)
                line = 'EOF'
            except KeyboardInterrupt:
                print()
                return
            if not loop:
                return


    @cli_method
    def help(self, func_name: str = None):
        """Display usage for a particular function."""
        if func_name is None:
            print(self.help.__doc__)
            return
        try:
            # Special cases properties to print both fget and fset docstrings.
            if func_name in self.property_getters: #Check if we have an @property
                print("Without parameters:")
                print("  ", self.property_getters[func_name].__doc__)
                print("With parameters:")
                try:
                    print("  ", self.cli_method_definitions[func_name]["doc"])
                except KeyError:
                    print()
                return

            # Normal case.
            if func_name in self.cli_methods:
                print(self.cli_method_definitions[func_name]["doc"])
                return
        except KeyError:
            print(f"Error: method {func_name} is not a valid command.")

