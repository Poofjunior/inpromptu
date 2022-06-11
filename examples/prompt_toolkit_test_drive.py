#!/usr/bin/env python3
from inpromptu.inpromptu_prompt_toolkit import Inpromptu
from test_drive import TestDrive


if __name__ == "__main__":
    my_test_drive = TestDrive()
    test_interface = Inpromptu(my_test_drive)
    test_interface.cmdloop()

