#!/usr/bin/env/python3
import pytest, autopy
from inpromptu import Inpromptu, cli_method

def test_normal_inheritance(monkeypatch, capsys):
    """Test that inheritance works"""
    # Create an inherited class that has a cli_method decorated class method.
    class TestInterface(Inpromptu):
        def __init__(self):
            super().__init__()

        @cli_method
        def test_method(cls):
            """dummy docstring."""
            pass

    def user_input_response(prompt):
        return "help test_method\r\n"
    monkeypatch.setattr('builtins.input', user_input_response)

    my_interface = TestInterface()
    my_interface.cmdloop(loop=False)

    # Reply for help should print the docstring for the help function.
    assert capsys.readouterr().out.rstrip() == TestInterface.test_method.__doc__

def test_nested_inheritance(monkeypatch, capsys):
    pass

def test_mulitple_inheritance(monkeypatch, capsys):
    pass
