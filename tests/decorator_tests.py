#!/usr/bin/env/python3
import pytest, autopy
from inpromptu import Inpromptu, cli_method


def test_fn_collection_on_atproperty(monkeypatch, capsys):
    """Test that @property decorator works"""
    # Create an inherited class that has a cli_method decorated class method.
    class TestInterface(Inpromptu):
        def __init__(self):
            super().__init__()

        @property
        @cli_method
        def at_property_method(self):
            """dummy docstring."""
            pass

    def user_input_response(prompt):
        return "at_property_method\r\n"
    monkeypatch.setattr('builtins.input', user_input_response)

    my_interface = TestInterface()
    my_interface.cmdloop(loop=False)
    # This should not raise an exception.

