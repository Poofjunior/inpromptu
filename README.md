# Inpromptu
A library for inferring interactive prompts from object instances.


## What Inpromptu Is
Inpromptu is a near-direct replacement for Python's built-in [cmd.py](https://docs.python.org/3/library/cmd.html) utility for rapidly creating *REPL* (read-evaluate-print-loop) interfaces.
But instead of rewriting an extra class with special `do_` methods, Inpromptu infers a prompt from the class directly using type hints--and even supports tab completion.

Born from a need to quickly interact with real-world devices and a frustration from the manual overhead of cmd.py, Inpromptu automatically generates an interactive prompt session by taking advantage of Python's type hinting and introspection capabilities.
Features include

* seamless automatic tab completion using a method's function signature
  * supports: `bool`, `int`, `float`, `str`, anything that inherits from `Enum`, and `@property`-decorated methods (getter and setters)
* automatic help generation directly from a method's docstring
* variable positional (`*args`) and keyword-only (`**kwds`) input

Inpromptu also provides a [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/master/)-compatible completer so you can build more complicated prompts while getting all of inpromptu's introspection elements for free.

## What Inpromptu Isn't
Inpromptu creates an interactive prompt. Inpromptu is not:
* a command line interface generator. See [argparse](https://docs.python.org/3/library/argparse.html), [python-fire](https://github.com/google/python-fire), or [click](https://click.palletsprojects.com/en/7.x/) for that.
* a api-replacement for cmd.py. There are some differences, mainly the lack of `do_` methods. Have a go at the examples.
* a GUI with graphical elements. See [magicgui](https://pyapp-kit.github.io/magicgui/) for a project in the same spirit.

## Requirements
* Python 3.6 or later
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

Create a prompt with Inpromptu.
```python
from inpromptu import Inpromptu

my_test_drive = TestDrive()
my_prompt = Inpromptu(my_test_drive)
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
Press **tab** twice to show all your callable attributes.
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
Press tab to complete any function.
```
>>> add_fuel
```
Put a space between the command and press **tab** twice.
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

So what are you waiting for? Why not take it for a test drive? From the example directory, run:

```
python3 test_drive.py
```

### Customization
It's possible to explicitly specify completions with the `set_completions` method.

```python
my_test_drive = TestDrive()
my_prompt = Inpromptu(my_test_drive)
my_prompt.set_completion_options('add_misc_item', 'stuff',
                                 ['fridge', 'kelp', 'biscuits',
                                  'the_one_ring', 'flux_capacitor'])
my_prompt.cmdloop()
```
Now entering the `add_misc_item` method and double-pressing the **tab** key should produce
```
>>> add_misc_item stuff=
biscuits        flux_capacitor  fridge          kelp            the_one_ring    
```

## FAQs
### Why not just use the Python shell?
Inpromptu is intented to be a minimalistic UI on its own.
Tab-completion and inferring of arguments by type (esp Enums) makes it easier to understand how to invoke the function that strictly by using the shell.

### Is there any way I can tease out the core elements to build my own interface?
Yes. In fact, core elements of Inpromptu can be hooked directly into [Python Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/en/master/) to provide the same kind of object-based completions with richer prompt features.
See the examples folder for some inspiration.

### What's not implemented?
* The [@overload](https://docs.python.org/3/library/typing.html#typing.overload) operator.
* functions wrapped in decorators: like `@cache`, `@cached_property` from functools
  * Note: some cases may work already.
* Recording a series of commands.

### What's Going to be Implemented Next?
* Explicit handling of functions wrapped in decorators.
* Overloading completions for specified functions

## Similar Projects
* [Kickoff](https://python-kickoff.readthedocs.io/en/latest/#)

## About the Author
Inpromptu was written by someone who used cmd.py one-too-many times.

