#!/usr/bin/env python3
"""Base Class for inferring an introspective prompt."""
import pprint
from abc import ABC, abstractmethod
from ast import literal_eval
from enum import Enum
from .object_method_manager import ObjectMethodManager
from .errors import UserInputError


# helper function for splitting user input containing nested {}, [], (), '', "".
def container_split(s):
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
        if c == " " and \
           (len(text_queue) == 0) and (len(container_queue) == 0):
            #print(f"{c} -> split here.")
            split_indices.append(i)
            continue
        #print(c)
    #print(split_indices)
    split_indices = [0] + split_indices + [len(s)]
    # Return a tuple
    return [s[x:y].lstrip() for x,y in zip(split_indices, split_indices[1:]) \
            if len(s[x:y].lstrip()) > 0] , \
            len(container_queue) == 0 and len(text_queue) == 0


class InpromptuBase(ABC):
    """Inspects an object and enables the invoking of any attribute's methods."""

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

    @abstractmethod
    def input(self):
        """Return input from the user."""
        # To be implemented by child classes.
        pass

    def _get_param_options(self, func_name, param_name, partial_val_text):
        """Return list of valid parameter completions."""
        func_param_completions = []
        # See if this type has a specific list of completions.
        param_opts = self.omm.method_defs[func_name]['parameters'][param_name].get('options', [])
        for param in param_opts:
            if param.startswith(partial_val_text):
                func_param_completions.append(param)
        return func_param_completions

    def _fn_value_from_string(self, fn_name, arg_name, val_str):
        """Convert param input from string to value appropriate for the signature."""
        param_type = self.omm.method_defs[fn_name]['parameters'][arg_name]['type']
        # Handle yucky edge case where "False" gets cast to True
        # for bools, we'll accept True or False only.
        if param_type == bool:
            if val_str not in ["True", "False"]:
                raise UserInputError("Error: valid options for bool type are " \
                                     "either True or False.")
            elif val_str == 'False':
                return False
        # Enum access by name (not by value) requires brackets.
        if issubclass(param_type, Enum):
            return param_type[val_str]
        # Remaining cases behave predictably.
        return param_type(literal_eval(val_str))

    def cmdloop(self, loop=True):
        """Repeatedly issue a prompt, accept input, and dispatch to action
        methods, passing them the line remainder as argument.
        """
        while True:
            try:
                line = self.input()
                if line.lstrip() == "":
                    continue
                ## Extract fn and args.
                fn_name, *arg_blocks = container_split(line)[0]
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
                    # Maybe keep pprint with a verbose option?
                    #pprint.pprint(kwargs)
                    return_val = self.omm.methods[fn_name](**kwargs)
                except Exception as e:
                    print(f"{fn_name} raised an exception while being executed.")
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


