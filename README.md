# Inpromptu
A library for inferring interactive prompts from object instances.


## What Inpromptu Is
Inpromptu is a near-direct replacement for Python's built-in [cmd.py](https://docs.python.org/3/library/cmd.html) utility.
Rather than rewrite an extra class with special `do_` methods, Inpromptu infers a prompt from the class directly.
Inpromptu takes an object instance's callables and exposes them in a read-evaluate-print-loop that supports tab-completion.

Born from a need to quickly interact with real-world devices and a frustration from the manual overhead of cmd.py, Inpromptu automatically generates an interactive prompt session by taking advantage of Python's type hinting and introspection capabilities.
Features include

* seamless automatic tab completion using a method's function signature
* automatic help generation using a method's docstring
* TODO: interactive methods that can prompt the user for more input anywhere in the method
  * customizeable tab-completion that can be reconfigured anywhere in the method

Inpromptu also provides a [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/master/)-compatible completer so you can build more complicated prompts while getting all of inpromptu's introspection elements for free.

## What Inpromptu Isn't
Inpromptu creates an interactive prompt. Inpromptu is not:
* a command line interface generator. See [argparse](https://docs.python.org/3/library/argparse.html), [python-fire](https://github.com/google/python-fire), or [click](https://click.palletsprojects.com/en/7.x/) for that.
* a api-replacement for cmd.py. There are some differences. Have a go at the examples.

## Requirements
* Python 3.7 or later
* all methods that will support completion must have all parameters type-hinted

## Installation
You can install this latest stable version of this package from PyPI with
````
pip install inpromptu
````

Or you can clone this repository and, from within this directory, install inpromptu in *editable* mode with
````
pip install -e .
````

## Example Time

Start with a class in file such as test_drive.py.
```python
class TestDrive:

    def __init__(self):
        """initialization!"""
        self.vehicle_speed = 0

    honk(self):
        """beep the horn."""
        print("Beep!")

    speed(self):
        """return the vehicle speed."""
        return self.vehicle_speed
```

Create a promt with Inpromptu.
```python
from inpromptu import Inpromptu

my_test_drive = TestDrive()
my_prompt = Inpromtu(my_test_drive)
my_prompt.cmdloop()
```

Run it!
```
python3 test_drive.py
```
This should produce a prompt:
```
>>>
```
Press tab twice to show all your callable attributes.
```
honk            speed
>>>
```

Great! Now let's demo argument completion.

First, add a function with [type-hinted annotations](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html#functions) for all input arguments (except self or cls).
```python
add_fuel(self, gallons: float = 0, top_off: bool = False):
    """Add fuel in gallons.""
    pass
```
Run it!
```
python3 test_drive.py
```
Start typing at the prompt
```
>>> add_f
```
Press tab to complete any `@cli_method` decorated function.
```
>>> add_fuel
```
Put a space between the command and press tab twice.
```
gallons=<float> top_off=<False>
>>> add_fuel 
```
Magic! At this point you can finish entering the command in many ways.
```
>>> add_fuel gallons=10 top_off=False
```
OR
```
>>> add_fuel 10 False
```
OR
```
>>> add_fuel 10 top_off=False
```
In other words, arguments can be filled out by name or by position or by a combination of position first, then by name--just like how *args and **kwds behave on normal python functions.

Last demo. Tab completion can be inferred automatically by the function signature. But what if you need to change it mid-function to suggest user input? No prob. Just add it to the completions list

**TODO: validate that this works in new version.**

```python
add_specs_from_user(self):
    """Add specs from user."""
    self.completions = ["2", "4", "6"]
    self.door_count = self.input("How many doors does this vehicle have?")
```
"Tabbing" for completions will render this list which is cleared when the function finishes executing.


So what are you waiting for? Why not take it for a test drive? From the top directory, run:

```
python3 -m examples.test_drive
```

## FAQs
### Why not just use the python shell?
You could! Inpromptu is intented to be a bit more minimalistic and user-friendly.
Inpromptu can be used as a minimalistic UI on its own.

Core elements of Inpromptu can also be hooked directly into [Python Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/en/master/) to provide the same kind of object-based completions with richer prompt features.

### What's not implemented?
* The [@overload](https://docs.python.org/3/library/typing.html#typing.overload) operator.
* input arguments that can be various types.
* functions wrapped in decorators: like `@cache`, `@cached_property` from functools
  * these may work. Double check.

## About the Author
Inpromptu was written by someone who used cmd.py one-too-many times. There had to be a better solution.
And Inpromptu is one of many.
