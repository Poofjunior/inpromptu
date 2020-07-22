## Inpromptu
A library for automatically inferring interactive prompts.


### What Inpromptu Is
Inpromptu is a near-direct replacement for Python's built-in [cmd.py](https://docs.python.org/3/library/cmd.html) utility.

Born from a need to quickly interact with real-world devices and a frustration from the manual overhead of cmd.py, Inpromptu automatically generates an interactive prompt session by taking advantage of Python's type hinting and introspection capabilities. Features include

* seamless automatic tab completion using a method's function signature
* automatic help generation using a method's docstring
* interactive methods that can prompt the user for more input anywhere in the method
  * customizeable tab-completion that can be reconfigured anywhere in the method

### What Inpromptu Isn't
Inpromptu creates an interactive prompt. Inpromptu is not:
* a command line interface generator. See [argparse](https://docs.python.org/3/library/argparse.html), [python-fire](https://github.com/google/python-fire), or [click](https://click.palletsprojects.com/en/7.x/) for that.
* a direct api-replacement for cmd.py. There are minor differences. Have a go at the examples.

## Requirements
* Python 3.6 or later
* classes that you wish to transform into interactive prompt sessions must inherit from the Inpromptu object
* methods that you wish to expose to the prompt session as commands must be decorated with the ```@cli_method``` decorator
* all methods that will become prompt commands must have all parameters type-hinted

## Example Time

Start with a class in file such as test_drive.py.
```python
class TestDrive(object):

    def __init__(self):
        """initialization!"""
        self.speed = 0
    
    honk(self):
        """beep the horn."""
        pass
    
    @property
    speed(self):
        """return the vehicle speed."""
        pass
```

Inherit from Inpromptu. Decorate your method with `@cli_method`.
```python
class TestDrive(Inpromptu):

    def __init__(self):
        """initialization!"""
        super().__init__(prompt=">>>")
        self.speed = 0
    
    @cli_method
    honk(self):
        """beep the horn."""
        pass
    
    @property
    @cli_method
    speed(self):
        """return the vehicle speed."""
        pass
```

Run it!
```
python3 test_drive.py
```
This should produce a prompt:
```
>>>
```
Press tab twice to show all your `@cli_method` decorated arguments.
```
honk            speed
>>>
```

Great! Now let's demo argument completion.

First, add a function with [type-hinted annotations](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html#functions) for all input arguments (except self or cls).
```python
@cli_method
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

So what are you waiting for? Why not take it for a test drive?


## About Me
Inpromptu was written by someone who used cmd.py one-too-many times. There had to be a better solution.... After writing Inpromptu, there was!
