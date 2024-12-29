#!/usr/bin/env python3
"""Base Class for inferring an introspective prompt."""
import logging
import pprint
import traceback
from abc import ABC, abstractmethod
from ast import literal_eval
from enum import Enum
from inspect import signature
from .object_method_manager import ObjectMethodManager
from .errors import UserInputError

# helper function for splitting user input containing nested {}, [], (), '', "".
def container_split(s: str, sep: str = " "):
    """split that splits on spaces while handling nested "", '', {}, [].

    returns a tuple (list, bool) of the split items and a bool indicating
            whether the final word was fully entered.
    """
    container_queue = []
    text_queue = []
    split_indices = []
    text_delim = {'"', "'"}
    container_start = { '{', '(', '[' }
    container_end = { '}', ')', ']' }
    container_end_to_start = { '}':'{', ')':'(', ']':'[' }

    for i, c in enumerate(s):
        if c in text_delim:
            if len(text_queue) == 0: # start of string.
                #print(f"{c} -> start of string") # start of string
                text_queue.append(c)
                continue
            elif len(text_queue) > 0 and c == text_queue[-1]:  # end of string.
                #print(f"{c} -> end of string") # end of string
                text_queue.pop(-1)
                continue
        elif c in container_start:
            #if len(container_queue) == 0: # start of outermost container.
            #    print(f"{c} -> start of outermost container")
            container_queue.append(c)
            continue
        elif c in container_end:
            if len(container_queue) > 0:
                if container_end_to_start[c] == container_queue[-1]:
                    container_queue.pop(-1)
                    if len(container_queue) == 0:
                        #print(f"{c} -> end of outermost container")
                        chunk_start = i+1
                        continue
        if c == sep and \
           (len(text_queue) == 0) and (len(container_queue) == 0):
            #print(f"{c} -> split here.")
            split_indices.append(i)
            continue
        #print(c)
    #print(split_indices)
    split_indices = [0] + split_indices + [len(s)]
    # Return a tuple
    return [s[x:y].lstrip(sep) for x,y in zip(split_indices, split_indices[1:]) \
            if len(s[x:y].lstrip()) > 0] , \
            len(container_queue) == 0 and len(text_queue) == 0


class InpromptuBase(ABC):
    """Inspects an object and enables the invoking of any attribute's methods."""

    prompt = '>>>'
    complete_key = 'tab'
    DELIM = ' '

    def __init__(self, class_instance, methods_to_skip = [], var_arg_subs = {}):
        """Constructor."""
        self.log = logging.getLogger(self.__class__.__name__)
        self.omm = ObjectMethodManager(class_instance,
                                       methods_to_skip=methods_to_skip,
                                       var_arg_subs=var_arg_subs)

        # In-function completions for calling input() within a fn.
        # Note that this variable must be cleared when finished with it.
        self.completions = None
        self.prompt = self.__class__.prompt

    @abstractmethod
    def input(self):
        """Return input from the user."""
        # To be implemented by child classes.
        pass

    def set_completion_options(self, method: str, parameter: str,
                               options: list[str]):
        """Specify an explicit set of completion options for a method parameter.
        Override existing options."""
        self.omm.set_completion_options(method, parameter, options)

    def get_completion_options(self, method: str, parameter: str):
        return self.omm.get_completion_options(method, parameter)

    def _get_param_options(self, func_name, param_name, partial_val_text):
        """Return list of valid parameter completions for the given input text."""
        func_param_completions = []
        # See if this type has a specific list of completions.
        param_opts = self.omm.method_defs[func_name]['parameters'][param_name].get('options', [])
        for param in param_opts:
            if param.startswith(partial_val_text):
                func_param_completions.append(param)
        return func_param_completions

    def _fn_param_from_string(self, fn_name, arg_name, val_str):
        """Convert param input from string to value appropriate for the signature."""
        if not val_str:
            raise ValueError(f"val_str cannot be empty.")
        param_types = self.omm.method_defs[fn_name]['parameters'][arg_name]['types']
        # Iterate through types. Try to convert input to enums first.
        for param_type in param_types:
            # Enum access by name (not by value) requires brackets.
            if issubclass(param_type, Enum):
                # Try to parse the input as an enum.
                try:
                    enum_class, name = val_str.split(".")
                    if enum_class == param_type.__name__:
                        return param_type[name]
                except (ValueError, KeyError):
                    pass
        # Try to convert to a valid type and return it.
        # Use literal_eval first to avoid unwanted conversions.
        # Handle bools, ints, floats, None, and strings enclosed in quotes.
        try:
            value = literal_eval(val_str)
            if type(value) in param_types:
                return value
        except ValueError:
            pass
        # Call each constructor manually.
        for param_type in param_types:
            try:
                return param_type(val_str)
            except (TypeError, ValueError):
                pass
        # Error if we made it this far.
        raise UserInputError(
            f"For function {fn_name} parameter {arg_name}, value "
            f"'{val_str}' could not be evaluated as any of the following "
            f"types: {param_types}.")

    def parse_args_from_input(self, line, sep=" "):
        """Parse line into args and kwargs with a custom delimiter.
        Raise syntax error if the line is not parsable.
        """
        arg_blocks, completed = container_split(line, sep)
        args = []
        kwargs = {}

        parsing_args = True
        for arg_block in arg_blocks:
            sub_block, _ = container_split(arg_block, '=')
            if len(sub_block) == 1 and parsing_args:
                args.append(sub_block[0])
            elif len(sub_block) == 1 and not parsing_args:
                raise SyntaxError("Args must be specified before kwargs.")
            elif len(sub_block) == 2:
                parsing_args = False
                kwargs[sub_block[0]] = sub_block[1]
            else:
                raise SyntaxError(f"Unparsable input: '{line}'")
        # completed will indicate if the last kwarg was fully input correctly.
        return args, kwargs, completed

    def cmdloop(self, loop=True):
        """Repeatedly issue a prompt, accept input, and dispatch to action
        methods, passing them the line remainder as argument.
        """
        while True:
            try:
                line = self.input()
                if line.lstrip() == "":
                    continue
                ## Extract fn and arg/kwarg blocks.
                try:
                    fn_name, args_and_kwargs = line.split(maxsplit=1)
                except ValueError:
                    fn_name = line.split()[0]
                    args_and_kwargs = ""
                args, kwargs, completed = self.parse_args_from_input(args_and_kwargs)
                self.log.warning(f"parsed args: {args}, kwargs: {kwargs}")
                # Extract function.
                # Property getter shortcut.
                if not args and not kwargs and fn_name in self.omm.property_getters:
                    func = self.omm.property_getters[fn_name]
                else:
                    func = self.omm.methods[fn_name]
                params = list(signature(func).parameters.keys())
                # Convert raw input to input appropriate for the signature.
                # FIXME: this is naive and doesn't parse Enums.
                args = [literal_eval(r) for r in args]
                kwargs = {k: literal_eval(v) for k, v in kwargs.items()}
                # Prepend 'self' or 'cls'.
                if params:
                    if params[0] == 'self':
                        args = [self.omm.class_instance] + args
                    if params[0] == 'cls':
                        args = [self.omm.class_instance.__class__] + args
                # Invoke the function
                return_val = None
                try:
                    self.log.warning(f"Calling fn {fn_name} with args: {args}, kwargs: {kwargs}")
                    return_val = func(*args, **kwargs)
                except Exception as e:
                    print(f"{fn_name} raised an exception while being executed.")
                    print(traceback.format_exc())
                # Reset any completions set during this function.
                finally:
                    self.completions = None
                if return_val is not None:
                    print(return_val)
            except (EOFError, ValueError, UserInputError) as e:
                print(traceback.format_exc())
            except KeyboardInterrupt:
                print()
                return
            if not loop:
                return

