#!/usr/bin/env/python3
from inpromptu.inpromptu import Inpromptu, cli_method


class TestDrive(Inpromptu):

    def __init__(self):
        """A test class demoing basic library usage."""
        super().__init__()
        self.vehicle_speed = 0
        self.gallons = 0

    @property
    @cli_method
    def speed(self):
        """return the current speed."""
        return self.vehicle_speed

    @cli_method
    def add_fuel(self, gallons: float = 0, top_off: bool = False):
        """add some fuel."""
        self.gallons += gallons


if __name__ == "__main__":
    test_interface = TestDrive()
    test_interface.cmdloop()
