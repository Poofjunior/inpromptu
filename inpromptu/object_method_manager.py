#!/usr/bin/env python3
"""Class for Inspecting and managing the methods of an object instance."""

from inspect import getmembers, ismethod, signature
from enum import Enum

# TODO: figure out how to warn against multipledispatch
# TODO: figure out clean way to trim out certain methods
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
                if attribute_name.startswith('__'): # skip hidden attributes.
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


    def __init__(self, class_instance, *args, method_ignore_list=[], **kwargs):
        """collect functions."""

        super().__init__(*args, **kwargs)
        self.class_instance = class_instance

        # Containers for methods and their signatures.
        # Methods decorated with @property become property objects which can
        # contain up to 3 methods: fget, fset, and fdel.
        # From the user perspective, fget and fset have the same name, but
        # different signature, so we hold onto all properties so that we can
        # invoke fgets separately.
        self.cli_methods, self.property_getters = self._get_cli_methods(method_ignore_list)
        # Insert a help method that prints the docstring into the callables.
        self.cli_methods['help'] = self.help
        self.callables = set({**self.cli_methods, **self.property_getters}.keys())
        self.cli_method_definitions = self._get_cli_method_definitions()


        #import pprint
        #print("cli methods")
        #pprint.pprint(self.cli_methods)
        #print("cli method definitions")
        #pprint.pprint(self.cli_method_definitions)
        #print("callables")
        #pprint.pprint(self.callables)


    def _get_cli_methods(self, method_ignore_list = []):
        """Collect all methods but avoid the ones in the method_ignore_list."""

        cli_methods = {}
        property_getters = {}


        for name in dir(self.class_instance):
            #print(name)
            # Custom fn since getmembers does not get functions decorated with @property
            value = get_dict_attr(self.class_instance, name)
            # Special case properties, which may be tied to 2 relevant methods.
            if isinstance(value, property):
                if value.fset is not None:
                    cli_methods[name] = value.fset
                if value.fget is not None:
                    # Store the getter elsewhere to prevent name clash
                    property_getters[name] = value.fget
            elif isinstance(value, classmethod):
                value = value.__func__
            # Skip over methods we should explicitly ignore.
            # Skip over special "dunder" methods.
            # Skip over anything that isn't callable.
            elif name in method_ignore_list or name.startswith('__') or \
                 not callable(value):
                continue
            else:
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
                    parameter["default"] = self.class_instance
                elif parameter_name == 'cls':
                    parameter["default"] = self.class_instance.__class__

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


    def help(self, func_name: str = None):
        """Print a cli method's docstring."""

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
                    print("  ", self.cli_method_definitions[func_name]["doc"])
                except KeyError:
                    print()
            # Normal Case:
            elif func_name in self.cli_methods:
                print(self.cli_method_definitions[func_name]["doc"])
            # Misspelling case, or callable does not exist.
            else:
                raise KeyError
        except KeyError:
            print(f"Error: {func_name} is not a callable method.")