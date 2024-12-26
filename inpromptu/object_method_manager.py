#!/usr/bin/env python3
"""Class for Inspecting and managing the methods of an object instance."""

import logging
import sys
from inspect import signature
from enum import Enum
from typing import Union
# For versions before python 3.7, we need the backport of get_origin
if sys.version_info < (3,7):
    from typing_extensions import get_origin, get_args
else:
    from typing import get_origin, get_args

# TODO: figure out how to warn against multipledispatch
# TODO: have a way of exporting and importing structure.

# Workaround because getmembers does not get functions decorated with @property
# https://stackoverflow.com/questions/3681272/can-i-get-a-reference-to-a-python-property
def get_dict_attr(class_def, attr):
    #for obj in [obj] + obj.__class__.mro():
    for obj in [class_def] + class_def.__class__.mro():
        if attr in obj.__dict__:
            return obj.__dict__[attr]
    raise AttributeError


class ObjectManager:
    """Inspects an object recursively and enables the invoking of any attribute's methods."""

    def __init__(self, class_instance):
        """Constructor."""

        def get_callable_dag(object_inst, indentation="    "):
            """Retrieve the directed acyclic graph for this object. (recursive)."""

            attributes = {}
            for attribute_name in dir(object_inst):
                if attribute_name.startswith('_'): # skip hidden attributes.
                    continue
                try:
                    value = get_dict_attr(object_inst, attribute_name)
                    # Skip non-userdefined classes since we don't care about their methods.
                    if value.__class__.__module__ in ['__builtins__', 'builtins']: # 3.6, 3.7+
                        continue
                    # Check if this object inst has callables.
                    print(indentation + attribute_name)
                    omm = ObjectMethodManager(value)
                    if len(omm.callables) == 0:
                        del omm
                        continue
                    #print(indentation + attribute_name)
                    attributes[attribute_name] = {"instance": value}
                    subattributes = get_callable_dag(value, indentation=indentation + "    ")
                    attributes[attribute_name]["attributes"] = subattributes
                except Exception as e:
                    print(indentation + str(e))
                    pass
            return attributes

        # Directed Acyclic Graph of all nested (nonbuiltin) object instances with callables.
        self.callable_dag = get_callable_dag(class_instance)
        import pprint
        pprint.pprint(self.callable_dag)


class ObjectMethodManager:
    """Inspects an object and aggregates its callable methods."""

    def __init__(self, class_instance, methods_to_skip = [], var_arg_subs = {}):
        """collect functions."""
        self.log = logging.getLogger(self.__class__.__name__)
        self.class_instance = class_instance

        # Containers for methods and their signatures.
        # Methods decorated with @property become property objects which can
        # contain up to 3 methods: fget, fset, and fdel.
        # From the user perspective, fget and fset have the same name, but
        # different signature, so we hold onto all properties so that we can
        # invoke fgets separately.
        self.methods, self.property_getters = self._get_methods(methods_to_skip)
        # Insert a 'help' method into the callables that prints the docstring.
        # Note: do this before calling _get_method_defs() so we get sig params.
        self.methods['help'] = self.help
        self.callables = set({**self.methods, **self.property_getters}.keys())
        self.method_defs = self._get_method_defs()
        # Provide help's arg completion options.
        self.method_defs['help']['parameters']['func_name']['types'] = [str]
        self.method_defs['help']['parameters']['func_name']['options'] = \
            [str(a) for a in self.callables]

        #self._apply_variable_argument_substitutions(var_arg_subs)

        #import pprint
        #print("cli methods")
        #pprint.pprint(self.methods)
        #print("cli method definitions")
        #pprint.pprint(self.method_defs)
        #print("callables")
        #pprint.pprint(self.callables)

    def _get_methods(self, method_ignore_list = []):
        """Collect all methods but avoid the ones in the method_ignore_list."""

        methods = {}
        property_getters = {}

        for name in dir(self.class_instance):
            #print(name)
            # Custom fn since getmembers does not get functions decorated with @property
            value = get_dict_attr(self.class_instance, name)
            # Special case properties, which may be tied to 2 relevant methods.
            if isinstance(value, property):
                if value.fset is not None:
                    methods[name] = value.fset
                if value.fget is not None:
                    # Store the getter elsewhere to prevent name clash
                    property_getters[name] = value.fget
            elif isinstance(value, classmethod):
                value = value.__func__
            # Skip over methods we should explicitly ignore.
            # Skip over special "dunder" methods.
            # Skip over anything that isn't callable.
            elif name in method_ignore_list or name.startswith('_') or \
                 not callable(value):
                continue
            else:
                methods[name] = value

        return methods, property_getters

    def _get_method_defs(self):
        """Build method definitions. Skip methods that are missing type hints.

        :return: Dictionary of method names mapped to their definitions.
        """
        definitions = {}
        for method_name, method in self.methods.items():
            parameters = {}
            param_order = []
            sig = signature(method)
            # FIXME: how does we handle functions wrapped in decorators??
            # Collapse to the function any wrapped functions.
            # This works only for function decorator wrappers using
            # functools.wraps to do the wrapping
            #while hasattr(method, "__wrapped__"):
            #    method = method.__wrapped__

            # Useful for parsing function signature.
            # https://docs.python.org/3/tutorial/controlflow.html#special-parameters
            missing_hints = []
            for parameter_name, param in sig.parameters.items():
                # Note: parameter_name does not include '*' or '**' prefix.
                param_order.append(parameter_name)
                param_data = {'kind': param.kind}
                param_types = []
                if param.annotation is not param.empty:
                    if get_origin(param.annotation) is Union:
                        param_types = list(get_args(param.annotation))
                    else:
                        param_types = [param.annotation]
                # Enforce type hinting for all decorated methods.
                if not param_types and parameter_name not in ['self', 'cls']:
                    missing_hints.append(param)
                    continue
                # Check for parameter default value. Populate self & cls.
                if param.default is not param.empty:
                    param_data["default"] = param.default
                elif parameter_name == 'self':
                    param_data["default"] = self.class_instance
                elif parameter_name == 'cls':
                    param_data["default"] = self.class_instance.__class__
                # Add enum completions for each enum type in the list of types.
                param_options = []
                for param_type in param_types:
                    if param_type is not None and issubclass(param_type, Enum):
                        param_options.extend([str(a) for a in param_type])
                    # Add bool completions.
                    elif param_type is bool:
                        param_options.extend(["True", "False"])
                # Populate non-empty dict fields.
                if param_options:
                    param_data['options'] = param_options
                if param_types:
                    param_data['types'] = param_types
                parameters[parameter_name] = param_data
            # Skip methods that do not have all parameters type hinted.
            if len(missing_hints):
                self.log.warning(f"Method: '{method_name}' is missing type hints for "
                                 f"the following parameters: {missing_hints}. "
                                 "Omitting this method.")
                continue
            # Create the top-level dictionary structure for this method.
            definitions[method_name] = \
            {
                "param_order": param_order,
                "parameters": parameters,
                "doc": method.__doc__
            }

        return definitions

    def help(self, func_name: str):
        """Print a cli method's docstring."""
        # This fn gets appended to the list of callable methods such that it
        # be be invoked like any other command.

        if func_name is None:
            print(self.help.__doc__)
            return

        try:
            # Special case for @property, since it is tied to multiple methods.
            if func_name in self.property_getters:
                print("Without parameters:")
                print("  ", self.property_getters[func_name].__doc__)
                try:
                    print("With parameters:")
                    print("  ", self.method_defs[func_name]["doc"])
                except KeyError:
                    print()
            # Normal Case:
            elif func_name in self.methods:
                print(self.method_defs[func_name]["doc"])
            # Misspelling case, or callable does not exist.
            else:
                raise KeyError
        except KeyError:
            print(f"Error: {func_name} is not a callable method.")

    def set_completion_options(self, method: str, parameter: str,
                           options: list[str]):
        """Specify a specific set of completion options for a method parameter.
         Override existing options."""
        self._check_method_completion_options(method, parameter)
        self.method_defs[method]['parameters'][parameter]['options'] = options

    def get_completion_options(self, method: str, parameter: str):
        """Get completion options for a method's parameter."""
        self._check_method_completion_options(method, parameter)
        return self.method_defs[method]['parameters'][parameter]['options']

    def _check_method_completion_options(self, method: str, parameter: str):
        if method not in self.methods:
            raise ValueError(f"{method} is not a valid method. Valid methods "
                             f"are: {self.methods}.")
        if parameter not in self.method_defs[method]['parameters']:
            raise ValueError(f"{parameter} is not a parameter of method: "
                f"{method}. Valid parameters are: {list(self.method_defs['method']['parameters'].keys())}.")

