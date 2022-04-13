#!/usr/bin/env python3
"""Class for ."""
import readline
import pprint
import os
from math import floor
import traceback

from .object_method_manager import ObjectMethodManager
from .errors import UserInputError


# helper function for displaying completions.
def print_columnized_list(my_list):
    """Prints a list as a set of columns, maximizing screen space."""
    max_string_len = max(map(len, my_list)) + 1 # add 1 for minimum whitespace.
    _, window_width = map(int, os.popen('stty size', 'r').read().split())
    # Longest string and window width dictate columnized printing output
    # Either we have multiple rows worth of printing, or we have a single
    # row spread out across the whole window.
    text_fits_on_one_row = max_string_len * len(my_list) < window_width
    column_count = len(my_list) if text_fits_on_one_row else floor(window_width/max_string_len)
    column_width = floor(window_width/len(my_list)) if text_fits_on_one_row else max_string_len
    list_iter = iter(my_list)
    list_item = next(list_iter)
    try:
        while True:
            for i in range(column_count):
                # Print item; fill the remaining column block with whitespace.
                print(f"{list_item:<{column_width}}", end="")
                list_item = next(list_iter)
            print()
    except StopIteration:
        pass # Done printing.


class Inpromptu:
    """Inspects an object recursively and enables the invoking of any attribute's methods."""

    prompt = '>>>'
    complete_key = 'tab'
    DELIM = ' '

    def __init__(self, class_instance):
        """Constructor."""
        self.omm = ObjectMethodManager(class_instance)

        # In-function completions for calling input() within a fn.
        # Note that this variable must be cleared when finished with it.
        self.completions = None
        self.prompt = self.__class__.prompt


    def _match_display_hook(self, substitution, matches, longest_match_length):
        """_match_display_hook wrapper so we can at least read the exception.

        As called by readline, exceptions called in _match_display_hook will not
        be caught in the main thread.
        """

        try:
            return self.__match_display_hook(substitution, matches, longest_match_length)
        except Exception as e:
            traceback.print_exc()


    def __match_display_hook(self, substitution, matches, longest_match_length):
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
            param_order = [f"{x}=" for x in self.omm.cli_method_definitions[self.func_name]['param_order']]
            # matches arrive alphebatized. Specify order according to original.
            matches = sorted(matches, key=lambda x: param_order.index(x))
            # Render argument matches with type.
            # Track argument index such that we only display valid options.
            for arg_completion in matches:
                arg = arg_completion.split("=")[0]
                arg_type = self.omm.cli_method_definitions[self.func_name]['parameters'][arg]['type']
                print(f"{arg}=<{arg_type.__name__}>", end=" ")
        print()
        print(self.prompt, readline.get_line_buffer(), sep='', end='', flush=True)


    def input(self, prompt=None):
        """Wrapper for prompt function.
        Enables tab-completion while preserving full prompt prefix."""
        # Override the prompt if a custom prompt is requested.
        if prompt:
            self.prompt = prompt + " "
        else:
            self.prompt = self.__class__.prompt + " "
        return input(self.prompt)


    def complete(self, text, state, *args, **kwargs):
        """_complete wrapper so we can at least read the exceptions.

        As called by readline, exceptions called in complete will not be caught
        in the main thread.
        """
        try:
            return self._complete(text, state, *args, **kwargs)
        except Exception as e:
            traceback.print_exc()



    def _complete(self, text, state, *args, **kwargs):
        """function invoked for completing partially-entered text.
        Formatted according to readline's set_completer spec:
        https://docs.python.org/3/library/readline.html#completion

        This fn is invoked upon pressing the TAB key.

        Note: this fn gets called by readline really weirdly.
        This fn gets called repeatedly with increasing values of state until
        the fn returns the available completions (list) or None.
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
            results = [fn for fn in self.omm.callables if fn.startswith(text) and fn != text]
            try:
                return results[state]
            except IndexError:
                return None

        # Complete the fn params.
        self.func_name = cmd_with_args[0]
        # Check to make sure func name was fully typed.
        if self.func_name not in self.omm.callables:
            return None
        param_signature = cmd_with_args[1:]
        self.func_params = self.omm.cli_method_definitions[self.func_name]['param_order']
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

        try:
            return func_param_completions[state]
        except IndexError:
            # IndexError means state has incremented too far, and we're done.
            return None


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
                if line.lstrip() == "":
                    continue
                ## Extract fn and args.
                fn_name, *arg_blocks = line.split()
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

                param_count = len(self.omm.cli_method_definitions[fn_name]['param_order'])
                param_order = self.omm.cli_method_definitions[fn_name]['param_order']
                # Remove self or cls from param count and arg list.
                if self.omm.cli_method_definitions[fn_name]['param_order'][0] in ['self', 'cls']:
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
                kwarg_settings = self.omm.cli_method_definitions[fn_name]['parameters']
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
                    pprint.pprint(kwargs)
                    return_val = self.omm.cli_methods[fn_name](**kwargs)
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


    def _fn_value_from_string(self, fn_name, arg_name, val_str):
        """Converts the fn parameter input from string to a value appropriate with the signature."""

        # Handle yucky edge case where "False" gets cast to True
        param_type = self.omm.cli_method_definitions[fn_name]['parameters'][arg_name]['type']
        # for bools, we'll accept True or False only.
        if param_type == bool:
            if val_str not in ["True", "False"]:
                raise UserInputError("Error: valid options for bool type are either True or False.")
            elif val_str == 'False':
                return False

        # Remaining cases behave predictably.
        return param_type(val_str)
