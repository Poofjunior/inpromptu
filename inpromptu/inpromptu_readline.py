#!/usr/bin/env python3
"""Class for inferring an introspective prompt."""
import readline
import os
from math import floor
import traceback

from .inpromptu_base import InpromptuBase
from .inpromptu_base import container_split


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


class Inpromptu(InpromptuBase):
    """Inspects an object and enables the invoking of any attribute's methods."""

    prompt = '>>>'
    complete_key = 'tab'
    DELIM = ' '

    def __init__(self, class_instance):
        """Constructor."""
        super().__init__(class_instance)
        readline.set_completer(self.complete)
        # Only split text to match on spaces. Default includes '{', '[', etc
        # which will be skipped by the results of text.
        readline.set_completer_delims("= ") # Split on equals and spaces.
        readline.set_completion_display_matches_hook(self._match_display_hook)
        readline.parse_and_bind(f"{self.__class__.complete_key}: complete")

        # In-function completions for calling input() within a fn.
        # Note that this variable must be cleared when finished with it.
        self.completions = None

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
        cmd_with_args, _ = container_split(line)
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
        # Render Function arg values if any exist:
        elif len(cmd_with_args[-1].split("=")) > 1:
            matches = sorted(matches)
            print_columnized_list(matches)
        # Render Function arg names.
        else:
            param_order = [f"{x}=" for x in self.omm.method_defs[self.func_name]['param_order']]
            # matches arrive alphebatized. Specify order according to original.
            matches = sorted(matches, key=lambda x: param_order.index(x))
            # Render argument matches with type.
            # Track argument index such that we only display valid options.
            for arg_completion in matches:
                arg = arg_completion.split("=")[0]
                arg_type = self.omm.method_defs[self.func_name]['parameters'][arg]['type']
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
        # Exceptions raised in this fn are not catchable so we must print them
        # manually.
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

        # readline delim must be set to ' ' such that {, [, (, etc aren't
        # skipped. "container_split" will handle when to match the text we get.
        text = text.lstrip() # what we are matching against.
        line = readline.get_line_buffer() # The whole line.
        cmd_with_args, last_word_finished = container_split(line)

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
        param_entries = cmd_with_args[1:]

        # Check to make sure func name has parameters and was typed correctly.
        if self.func_name not in self.omm.method_defs:
            return None
        # remaining params to complete stored in self.func_params.
        self.func_params = self.omm.method_defs[self.func_name]['param_order']
        if self.func_params[0] in {'self', 'cls'}:
            self.func_params = self.func_params[1:]

        # First filter out already-entered positional arguments.
        # Abort upon first keyword.
        first_kwarg_found = False
        first_kwarg_index = 0
        param_entries = cmd_with_args[1:] # everything typed after the fn name.
        for entry_index, text_block in enumerate(param_entries):
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
            if text_block == param_entries[-1] and line[-1] is not self.__class__.DELIM:
                break
            first_kwarg_index += 1
        self.func_params = self.func_params[first_kwarg_index:]

        #print(f"found kwarg: {first_kwarg_found} | at index {first_kwarg_index}")
        #print(f"unfiltered params: {self.func_params}")

        # Then generate completion list from remaining possible params.
        func_param_completions = []
        for param_order_index, param_name in enumerate(self.func_params):
            completion = f"{param_name}="
            # No space case: <kwarg_name>=<value> is partially typed or fully typed but missing a space
            if line[-1] is not self.__class__.DELIM and \
                param_entries[-1].startswith(completion):
                partial_val_text = param_entries[-1].split('=')[-1]
                func_param_completions = self._get_param_options(self.func_name,
                                                                 param_name,
                                                                 partial_val_text)
                break
            # Bail early if the user entered unfinished text that can't be
            # completed with predefined options.
            if not last_word_finished:
                return None
            # Filter out already-populated argument options by name and position.
            skip = False
            for text_block in param_entries:
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

