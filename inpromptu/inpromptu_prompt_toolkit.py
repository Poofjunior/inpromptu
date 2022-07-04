#!/usr/bin/env python3
"""Prompt-toolkit implementation of Inpromptu."""

from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.completion import Completer, Completion
from .inpromptu_base import InpromptuBase
from .inpromptu_base import container_split


class Inpromptu(InpromptuBase):
    """Inspects an object and enables the invoking of any attribute's methods."""

    def __init__(self, class_instance):
        """Constructor."""
        super().__init__(class_instance)
        self.completions = None # unused for now.

        self.session = PromptSession(self.prompt, completer=self)

    def input(self):
        return self.session.prompt(self.prompt + " ",
                                   complete_style=CompleteStyle.READLINE_LIKE)

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
        display={} # what to show onscreen as the completion option.

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
            param_entries = cmd_with_args[1:]
            for entry_index, param_entry in enumerate(param_entries):
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
                if param_entry == param_entries[-1] and line[-1] != self.__class__.DELIM:
                    break
                first_kwarg_index += 1

            self.func_params = self.func_params[first_kwarg_index:]

            #print(f"found kwarg: {first_kwarg_found} | at index: {first kwarg_index}")
            #print(f"unfiltered params: {self.func_params}")

            # Now generate completion list for params not yet entered.
            for param_order_index, param_name in enumerate(self.func_params):
                completion = f"{param_name}="
                # No space case: <kwarg_name>=<value> is partially typed or fully typed but missing a space.
                if line[-1] != self.__class__.DELIM and \
                    param_entries[-1].startswith(completion):
                    partial_val_text = param_entries[-1].split('=')[-1]
                    func_param_completions = \
                        self._get_param_options(self.func_name,
                                                param_name,
                                                partial_val_text)
                    completions = [completion+v for v in func_param_completions]
                    display = {completion+v:v for v in func_param_completions}
                    break
                # Bail early if the user entered unfinished text that can't be
                # completed with predefined options.
                if not last_word_finished:
                    return
                # Filter out already-populated argument options by name and position.
                skip = False
                for param_entry in param_entries:
                    if param_entry.startswith(completion):
                        skip = True
                        break
                # regular check
                if completion.startswith(word) and not skip:
                    completions.append(completion)
                    display[completion] = completion

        # Finally, yield any completions.
        for completion in completions:
            yield Completion(completion,
                             start_position=-len(word),
                             display=display.get(completion, completion),
                             display_meta=None,
                             style="bg:ansiblack fg:ansiyellow")

