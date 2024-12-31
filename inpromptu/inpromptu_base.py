#!/usr/bin/env python3
"""Base Class for inferring an introspective prompt."""
import inspect
import logging
import pprint
import traceback
import typing
from abc import ABC, abstractmethod
from ast import literal_eval
from collections import OrderedDict
from enum import Enum
from inspect import signature, Parameter
from inspect import _ParameterKind as ParamKind
from .object_method_manager import ObjectMethodManager
from .errors import UserInputError


# FIXME: should container_split('key=', '=') return (['key=', ''], True) or (['key='], False) ?
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

    def __init__(self, class_instance, methods_to_skip=[], var_arg_subs={}):
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

    #def get_remaining_params(self, func, arg_blocks, skip_self_or_cls = True):
    #    """For a given function and given list of arguments, return the
    #    remaining parameters.

    #    Raise SyntaxError if input params are invalid.
    #    """
    #    positional_params = [ParamKind.POSITIONAL_ONLY, ParamKind.POSITIONAL_OR_KEYWORD]
    #    keyword_params = [ParamKind.POSITIONAL_OR_KEYWORD, ParamKind.KEYWORD_ONLY]
    #    sig = signature(func)
    #    remaining_params = list(sig.parameters.values())

    #    if skip_self_or_cls and remaining_params \
    #        and remaining_params[0].name in ['self', 'cls']:
    #        remaining_params.pop(0)
    #    # Handle bail-early case.
    #    if not len(remaining_params) and not arg_blocks:
    #        return []
    #    # Handle remaining cases.
    #    # Match param to input (arg or kwarg).
    #    parsing_kwargs = False  # Used to enforce args before kwargs
    #    for index, arg_block in enumerate(arg_blocks):
    #        sub_block, finished = container_split(arg_block, '=')
    #        last_block = (index == (len(arg_blocks) - 1))
    #        input_is_kwarg = len(sub_block) == 2
    #        parsing_kwargs = input_is_kwarg or parsing_kwargs
    #        next_param = remaining_params[0]
    #        try:
    #            # arg cases
    #            if not parsing_kwargs:
    #                if next_param.kind in positional_params:
    #                    remaining_params.pop(0)
    #                    continue
    #                if next_param.kind == ParamKind.VAR_POSITIONAL:
    #                    continue
    #            # kwarg cases.
    #            # Remove any *args present as soon as we start seeing kwargs.
    #            if parsing_kwargs and next_param.kind == ParamKind.VAR_POSITIONAL:
    #                remaining_params.pop(0)
    #                next_param = remaining_params[0]
    #            # Ensure final kwarg was fully entered. i.e: something after '='
    #            if last_block and (not finished or (sub_block[1] == "")):
    #                continue
    #            if next_param.kind in keyword_params:
    #                remaining_params.pop(0)
    #                continue
    #            if next_param.kind == ParamKind.VAR_KEYWORD:
    #                continue
    #            raise SyntaxError(f"Invalid parameter input: '{arg_block}' "
    #                              f"for parameter: {next_param.name}.")
    #        except IndexError:
    #            raise SyntaxError(f"Too many input arguments for the function: {func}.")
    #    return remaining_params

    @staticmethod
    def get_types(param: Parameter):
        """Return a list of valid Python types for a given parameter.
        """
        if param.annotation is Parameter.empty:
            return [typing.Any]
        if typing.get_origin(param.annotation) is typing.Union:
            return list(typing.get_args(param.annotation))
        return [param.annotation]

    @staticmethod
    def typed_eval(val_str, types):
        """Evaluate string to an object representation according to type hint.
        For Union types, types are evaluated in order.
        """
        # TODO: long-term we should be able to handle recursive type hinting.
        # Use literal_eval first to avoid unwanted literal conversions
        # from naively calling a literal constructor on the string representation.
        try:
            value = literal_eval(val_str)
        except ValueError:  # Enums cannot be evaluated this way.
            value = val_str
        for obj_type in types:
            # Enum access by name (not by value) requires brackets.
            if issubclass(obj_type, Enum):
                # Try to parse the input as an enum.
                try:
                    enum_class, name = val_str.split(".")
                    if enum_class == obj_type.__name__:
                        return obj_type[name]  # Use dict-like access.
                except (ValueError, KeyError):
                    pass
            try:
                return obj_type(value)  # Call constructor.
            except ValueError:  # This constructor didn't work. Move on.
                pass
        raise ValueError(f"Cannot convert {val_str} to any of the following "
                         f"types: {types}")

    def parse_args(self, func, arg_blocks, skip_self_or_cls: bool = True,
                   remaining_params_only: bool = False):
        """For a given function and list of parameter inputs, parse out:
        entered args, kwargs, remaining parameters, and

        Raise SyntaxError if input params are invalid.
        """
        args = []
        kwargs = {}
        positional_params = [ParamKind.POSITIONAL_ONLY, ParamKind.POSITIONAL_OR_KEYWORD]
        keyword_params = [ParamKind.POSITIONAL_OR_KEYWORD, ParamKind.KEYWORD_ONLY]
        sig = signature(func)
        remaining_params = OrderedDict(sig.parameters)
        # Find **kwargs parameter if it exists.
        varkwarg_search = [p for p in remaining_params.values() if p.kind == ParamKind.VAR_KEYWORD]
        has_varkwargs = len(varkwarg_search) > 0
        varkwarg_param = varkwarg_search[0] if len(varkwarg_search) else None

        if skip_self_or_cls and remaining_params \
                and list(remaining_params.values())[0].name in ['self', 'cls']:
            remaining_params.popitem(last=False)
        # Handle bail-early case: no params and no input.
        if not len(remaining_params) and not arg_blocks:
            return args, kwargs, list(remaining_params.values())
        # Handle remaining cases.
        # Match param to input (arg or kwarg).
        parsing_kwargs = False  # Used to enforce args before kwargs
        for index, arg_block in enumerate(arg_blocks):
            sub_block, finished = container_split(arg_block, '=')
            last_block = (index == (len(arg_blocks) - 1))
            input_is_kwarg = len(sub_block) == 2
            parsing_kwargs = input_is_kwarg or parsing_kwargs
            next_param = list(remaining_params.values())[0]
            param_types = self.get_types(next_param)
            if input_is_kwarg and (next_param.kind == ParamKind.POSITIONAL_ONLY):
                raise SyntaxError(f"Next parameter {next_param.name} is position-only.")
            try:
                # arg cases
                if not parsing_kwargs:
                    arg = sub_block[0]
                    if next_param.kind in positional_params:
                        remaining_params.popitem(last=False)
                        if remaining_params_only: # skip populating args.
                            continue
                        args.append(self.typed_eval(arg, param_types))
                        continue
                    if next_param.kind == ParamKind.VAR_POSITIONAL:
                        if remaining_params_only: # skip populating args.
                            continue
                        args.append(self.typed_eval(arg, param_types))
                        continue
                # kwarg cases.
                # Remove any *args present as soon as we start seeing kwargs.
                if parsing_kwargs and next_param.kind == ParamKind.VAR_POSITIONAL:
                    remaining_params.popitem(last=False)
                    next_param = list(remaining_params.values())[0]
                    param_types = self.get_types(next_param)
                # Ensure final kwarg was fully entered. i.e: something after '='
                if last_block and (not finished or (sub_block[1] == "")):
                    continue
                kwarg_name, kwarg_val = sub_block
                # kwargs can be input in any order.
                if kwarg_name in remaining_params:
                    del remaining_params[kwarg_name]
                    if remaining_params_only: # skip populating args.
                        continue
                    kwargs[kwarg_name] = self.typed_eval(kwarg_val, param_types)
                    continue
                # if **kwargs is present, we don't pop it until the end.
                # Technically, this param will always remain.
                elif has_varkwargs:
                    if remaining_params_only: # skip populating args.
                        continue
                    kwargs[kwarg_name] = self.typed_eval(varkwarg_param, param_types)
                    continue
                raise SyntaxError(f"Invalid parameter input: '{arg_block}' "
                                  f"for parameter: {next_param.name}.")
            except IndexError:
                raise SyntaxError(f"Too many input arguments for the function: {func}.")
        return args, kwargs, list(remaining_params.values())

    def get_remaining_params(self, func, arg_blocks, skip_self_or_cls = True):
        return self.parse_args(func, arg_blocks, skip_self_or_cls=skip_self_or_cls,
                               remaining_params_only=True)[2]

    def cmdloop(self, loop=True):
        """Repeatedly issue a prompt, accept input, and dispatch to action
        methods, passing them the line remainder as argument.
        """
        while True:
            try:
                line = self.input()
                if line.lstrip() == "":
                    continue
                # Extract fn and arg/kwarg blocks.
                try:
                    fn_name, args_and_kwargs_str = line.split(maxsplit=1)
                except ValueError:
                    fn_name = line.split()[0]
                    args_and_kwargs_str = ""
                # Extract function.
                # Property getter shortcut.
                if not args_and_kwargs_str.strip() and fn_name in self.omm.property_getters:
                    func = self.omm.property_getters[fn_name]
                else:
                    func = self.omm.methods[fn_name]
                args_and_kwargs, _ = container_split(args_and_kwargs_str)
                params = list(signature(func).parameters.keys())
                # Convert raw input to input appropriate for the signature.
                args, kwargs, _ = self.parse_args(func, args_and_kwargs)
                # Prepend 'self' or 'cls'.
                if params:
                    if params[0] == 'self':
                        args = [self.omm.class_instance] + args
                    if params[0] == 'cls':
                        args = [self.omm.class_instance.__class__] + args
                # Invoke the function
                return_val = None
                try:
                    self.log.debug(f"Calling fn {fn_name} with args: {args}, "
                                   f"kwargs: {kwargs}")
                    return_val = func(*args, **kwargs)
                except Exception as e:
                    self.log.error(f"{fn_name} raised an exception while being executed.")
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

