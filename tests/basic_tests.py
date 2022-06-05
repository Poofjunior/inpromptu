#!/usr/bin/env/python3
import pytest
from inpromptu import Inpromptu


# Basic Callable Collection
class TestClass:
    __test__ = False # Tell pytest not to collect the class itself as a test.

    def __init__(self):
        pass

    def my_method(self):
        return

    def my_other_method(self):
        return

def test_basic_callable_capture(monkeypatch, capsys):
    """Ensure that Inpromptu captures callables."""

    my_class_a = TestClass()
    my_prompt = Inpromptu(my_class_a)

    # Ensure that we retrieved all the class' methods. Note: 'help' is builtin.
    assert my_prompt.omm.callables == {'my_method', 'my_other_method', 'help'}, \
        "Error: ObjectMethodManager did not retrieve the correct methods of "\
        f"{my_class_a.__class__.__name__}"


# User-Input Template
# for tests that need to receive user input and inspect output printed to the
# shell, use this fn as a template.
def test_user_input_hookup(monkeypatch, capsys):
    """Spoof user input."""

    def user_input_response(prompt_input):
        """Send a when provided with an input string from the prompt.
           This fn acts as a user replying to the prompt_input."""
        return "my_method\r\n" # The equivalent of pressing <ENTER>

    # Hookup our custom response to act as user input.
    monkeypatch.setattr('builtins.input', user_input_response)

    my_prompt = Inpromptu(TestClass())

    # This will produce an input. Monkeypatched input fn should reply with
    my_prompt.cmdloop(loop=False)

    # Reply for help should print the docstring for the help function.
    assert capsys.readouterr().out.rstrip() == "" # Should not produce any output


# Ignoring of a class's non-callable objects
class TestClassWithMember:
    __test__ = False

    def __init__(self):
        self.my_data_member = 0

    def my_method(self):
        return

    def my_other_method(self):
        return

def test_ignore_non_callable_data_members(monkeypatch, capsys):
    """Ensure that Inpromptu ignores noncallable class members."""

    my_class_a = TestClassWithMember()
    my_prompt = Inpromptu(my_class_a)

    # Ensure that we retrieved all the class' methods. Note: 'help' is builtin.
    correct_callables = {'my_method', 'my_other_method', 'help'}
    assert my_prompt.omm.callables == correct_callables, \
        "Error: ObjectMethodManager did not ignore " \
        f"{my_class_a.__class__.__name__}'s non-callable objects."


# Keeping a class's callable objects that aren't methods
class MyCallable:
    def __call__(self):
        print("Hello.")

class TestClassWithCallableMember:
    __test__ = False

    def __init__(self):
        self.my_callable = MyCallable() # This should appear in callable's list

    def my_method(self):
        return

    def my_other_method(self):
        return

def test_keep_callable_data_members(monkeypatch, capsys):
    """Ensure that Inpromptu captures callable objects that aren't methods."""

    my_class_a = TestClassWithCallableMember()
    my_prompt = Inpromptu(my_class_a)

    # Ensure that we retrieved all the class' methods. Note: 'help' is builtin.
    correct_callables = {'my_method', 'my_other_method', 'my_callable', 'help'}
    assert my_prompt.omm.callables == correct_callables, \
        "Error: ObjectMethodManager did not include " \
        f"{my_class_a.__class__.__name__}'s callable objects."
