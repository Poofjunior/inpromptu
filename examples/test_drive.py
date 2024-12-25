#!/usr/bin/env python3
from inpromptu import Inpromptu
from enum import Enum, auto

from typing import Union

class Gear(Enum):
    crash_pads = auto()
    dance_shoes = auto()
    mysterious_fossil = auto()

class Junk(Enum):
    old_sofa = auto()
    vanity = auto()


class TestDrive:

    def __init__(self):
        """A test class demoing basic library usage."""
        super().__init__()
        self.vehicle_speed = 0
        self.gallons = 0
        self.num_doors = 0
        self.passengers = []
        self.car_name = "first car"

    @property
    def name(self):
        """name the car."""
        return self.car_name

    @name.setter
    def name(self, name: str):
        """return the current name."""
        self.car_name = name

    @property
    def speed(self):
        """return the current speed."""
        return self.vehicle_speed

    @speed.setter
    def speed(self, mph: float = 0):
        """Set the current speed"""
        self.vehicle_speed = mph

    def add_fuel(self, gallons: Union[float , None], top_off: bool = False):
        """add some fuel."""
        if gallons:
            self.gallons += gallons

    def add_passengers(self, passenger_list: list, buckle_them: bool = True):
        self.passengers = passenger_list
        for passenger in self.passengers:
            buckle_str = "" if buckle_them else "NOT "
            print(f"adding {passenger} and {buckle_str}buckling them.")

    def add_gear(self, gear: Gear):
        print(f"adding {gear}")

    def add_misc_item(self, stuff: Union[Gear, Junk, str]):
        print(f"adding {str(stuff)}.")

    def add_specs_from_user_input(self):
        """Add specs from the user."""
        # This in-function prompt needs custom completions.
        self.completions = ["2", "4", "6"]
        self.num_doors = int(self.input("How many doors does your vehicle have?\r\n"))

    @property
    def door_count(self):
        """The number of doors."""
        return self.num_doors

    def hotwire(self):
        """Hotwire the car. This should not appear in the interface if it was
        placed in the methods-to-skip list."""
        return


if __name__ == "__main__":
    test_interface = Inpromptu(TestDrive(), methods_to_skip=['hotwire'])
    test_interface.cmdloop()
