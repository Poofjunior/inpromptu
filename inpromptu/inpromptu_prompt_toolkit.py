#!/usr/bin/env python3
"""Prompt-toolkit implementation of Inpromptu."""

import pprint
import os
from math import floor
import traceback
from ast import literal_eval
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.completion import Completer, Completion

# TODO: rename inpromptu inpromptu_base
from .inpromptu import container_split
from .object_method_manager import ObjectMethodManager
from .errors import UserInputError



class Inpromptu:
    """Inspects an object and enables the invoking of any attribute's methods."""

    prompt = '>>> '
    complete_key = 'tab'
    DELIM = ' '

    def __init__(self, class_instance):
        """Constructor."""
        self.omm = ObjectMethodManager(class_instance)
        self.prompt = self.__class__.prompt
        self.completions = None # unused for now.


    def _fn_value_from_string(self, fn_name, arg_name, val_str):
        """Converts param input from string to value appropriate for the signature."""
        param_type = self.omm.method_defs[fn_name]['parameters'][arg_name]['type']
        # Handle yucky edge case where "False" gets cast to True
        # for bools, we'll accept True or False only.
        if param_type == bool:
            if val_str not in ["True", "False"]:
                raise UserInputError("Error: valid options for bool type are " \
                                     "either True or False.")
            elif val_str == 'False':
                return False
        # Remaining cases behave predictably.
        return param_type(literal_eval(val_str))


    def get_completions(self, document, complete_event):
        """yields completions for invoking a function with its parameters.

        The function will be entered in the form:

        <func_name> <arg_0_val> <arg_1_val> <kwarg_0_name>=<kwarg_0_val>, ...

        All positional arguments are required.
        Kwargs are optional and will take their default value if unspecified.

        positional arguments can also be called out by name like kwargs, i.e:
        <func_name> <arg_0_name>=<arg_0_val>
        but all following args must be called out this way.
        """
        # TODO: maybe it's worth just writing a REGEX for this?

        #word = document.get_word_before_cursor()
        text = document.text
        word = container_split(text)[0][-1] if (len(text) and text[-1] != " ") else ""
        # Check word against valid completions.
        line = document.lines[0]
        cmd_with_args, last_word_finished = container_split(line)
        completions = []

        # Complete the fn name.
        if len(cmd_with_args) == 0 or \
            (len(cmd_with_args) == 1 and line[-1] != self.__class__.DELIM):
                completions = [c for c in self.omm.callables if c.startswith(word)]
        # Complete the fn params (i.e: args in order then kwargs by name)
        else:
            self.func_name = cmd_with_args[0]
            # Check to make sure func name has parameters and was typed correctly.
            if self.func_name not in self.omm.method_defs:
                return None
            self.func_params = self.omm.method_defs[self.func_name]['param_order']
            if self.func_params[0] in ['self', 'cls']:
                self.func_params = self.func_params[1:]

            # First filter out already-entered positional arguments.
            # Abort upon finding first keyword argument.
            first_kwarg_found = False
            first_kwarg_index = 0
            param_signature = cmd_with_args[1:]
            for entry_index, param_entry in enumerate(param_signature):
                kwarg = None
                # Check if text entry is a fully-entered kwarg.
                for param_order_index, param_name in enumerate(self.func_params):
                    # kwargs are indentified by the string: "kwarg_name=kwarg_val"
                    completion = f"{param_name}="
                    #print(f"param_entry: {param_entry} | completion: {complection}")
                    if param_entry.startswith(completion):
                        kwarg = param_name
                        if not first_kwarg_found:
                            first_kwarg_found = True
                            first_kwarg_index = entry_index
                        break
                if first_kwarg_found:
                    break
                # Don't remove the last element if it is not fully entered.
                if param_entry == param_signature[-1] and line[-1] != self.__class__.DELIM:
                    break
                first_kwarg_index += 1

            self.func_params = self.func_params[first_kwarg_index:]

            #print(f"found kwarg: {first_kwarg_found} | at index: {first kwarg_index}")
            #print(f"unfiltered params: {self.func_params}")

            # Now generate completion list for params not yet entered.
            for param_order_index, param_name in enumerate(self.func_params):
                completion = f"{param_name}="
                if not last_word_finished:
                    return
                # No space case: arg is fully typed but missing a space.
                if line[-1] != self.__class__.DELIM and \
                    param_signature[-1].startswith(completion) and \
                    last_word_finished:
                    return
                # Filter out already-populated argument options by name and position.
                skip = False
                for param_entry in param_signature:
                    if param_entry.startswith(completion):
                        skip = True
                        break
                # regular check
                if completion.startswith(word) and not skip:
                    completions.append(completion)

        # Finally, yield any completions.
        for completion in completions:
            yield Completion(completion,
                             start_position=-len(word),
                             display=completion,
                             display_meta=None,
                             style="bg:ansiblack fg:ansiyellow")


    def cmdloop(self, loop=True):
        """Repeatedly issue a prompt, accept input, and dispatch to action
        methods, passing them the line remainder as argument.
        """

        session = PromptSession(self.prompt, completer=self)
        while True:
            try:
                text = session.prompt(self.prompt,
                                      complete_style=CompleteStyle.READLINE_LIKE)
                if text.lstrip() == "":
                    continue
                ## Extract fn and args.
                fn_name, *arg_blocks = container_split(text)[0]
                kwargs = {}

                no_more_args = False # indicates end of positional args in fn signature

                # Check if fn even exists.
                if fn_name not in self.omm.callables:
                    raise UserInputError(f"Error: {fn_name} is not a valid command.")

                # Shortcut for @property getters which have no parameters and
                # whose function pointers are stored elsewhere to prevent name
                # name clashing with their setters.
                if len(arg_blocks) == 0 and fn_name in self.omm.property_getters:
                    return_val = None
                    try:
                        this = self.omm.class_instance
                        # FIXME: how should we implement this?
                        #return_val = self.omm.property_getters[fn_name](self)
                        return_val = self.omm.property_getters[fn_name](this)
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

                param_count = len(self.omm.method_defs[fn_name]['param_order'])
                param_order = self.omm.method_defs[fn_name]['param_order']
                # Remove self or cls from param count and arg list.
                if self.omm.method_defs[fn_name]['param_order'][0] in ['self', 'cls']:
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
                    val = self._fn_value_from_string(fn_name, arg_name, val_str)
                    kwargs[arg_name] = val

                # Populate missing params with their defaults.
                # Raise error if are required param is missing.
                kwarg_settings = self.omm.method_defs[fn_name]['parameters']
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
                    # Maybe keep the pprinting with a verbose option?
                    #pprint.pprint(kwargs)
                    return_val = self.omm.methods[fn_name](**kwargs)
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
