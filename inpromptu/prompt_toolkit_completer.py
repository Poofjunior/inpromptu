#!/usr/bin/env python3
"""Class for a Prompt-Toolkit compatible completer."""
from prompt_toolkit.completion import Completer, Completion
from .object_method_manager import ObjectMethodManager
from .errors import UserInputError


class PromptToolkitCompleter(Completer):


    DELIM = ' '

    def __init__(self, class_to_complete, *args, **kwargs):
        """Create a completer from inferring all callables in a class instance."""

        super().__init__(*args, **kwargs)
        self.omm = ObjectMethodManager(class_to_complete)

        self.func_name = None
        self.func_params = None


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

        word = document.get_word_before_cursor()
        # Check word against valid completions.
        line = document.lines[0]
        cmd_with_args = line.split()
        completions = []

        # Complete method or @property names.
        if len(cmd_with_args) == 0 or \
            (len(cmd_with_args) == 1 and line[-1] !=self.__class__.DELIM):
            completions = self.omm.callables
        # Complete method parameters (i.e: args in order then kwargs by name)
        else:
            self.func_name = cmd_with_args[0]
            # Check to make sure func name was fully typed.
            if self.func_name not in self.omm.callables:
                return None
            param_signature = cmd_with_args[1:]
            self.func_params = self.omm.cli_method_definitions[self.func_name]['param_order']
            if self.func_params[0] in ['self', 'cls']:
                self.func_params = self.func_params[1:]

            # First filter out already-entered positional arguments.
            # Abort upon finding first keyword argument.
            first_kwarg_found = False
            first_kwarg_index = 0
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
                # No space case: arg is fully typed but missing a space.
                if line[-1] != self.__class__.DELIM and param_signature[-1].startswith(completion):
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
            if completion.startswith(word):
                yield Completion(completion,
                                 start_position=-len(word),
                                 display=completion,
                                 display_meta=None,
                                 style="bg:ansiblack fg:ansiyellow")

