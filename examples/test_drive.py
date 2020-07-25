#!/usr/bin/env/python3
from inpromptu import Inpromptu, cli_method, UserInputError


class TestDrive(Inpromptu):

    def __init__(self):
        """A test class demoing basic library usage."""
        super().__init__()
        self.vehicle_speed = 0
        self.gallons = 0
        self.num_doors = 0

    @property
    @cli_method
    def speed(self):
        """return the current speed."""
        return self.vehicle_speed

    @speed.setter
    @cli_method
    def speed(self, speed: float = 0):
        """Set the current speed"""
        self.vehicle_speed = speed

    @cli_method
    def add_fuel(self, gallons: float = 0, top_off: bool = False):
        """add some fuel."""
        self.gallons += gallons

    @cli_method
    def add_specs_from_user_input(self):
        """Add specs from the user."""
        # This in-function prompt needs custom completions.
        self.completions = ["2", "4", "6"]
        self.num_doors = int(self.input("How many doors does your vehicle have?\r\n"))

    @property
    @cli_method
    def door_count(self):
        """The number of doors."""
        return self.num_doors


if __name__ == "__main__":
    test_interface = TestDrive()
    test_interface.cmdloop()
