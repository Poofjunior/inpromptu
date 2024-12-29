#!/usr/bin/env/python3
import pytest
from inpromptu.inpromptu_base import container_split


def test_basic_split():

    basic_input = "hello there buddy"
    result = container_split(basic_input)
    assert result[0] == basic_input.split() and result[1] == True


def test_basic_custom_delimiter():

    basic_input = "hello|there|buddy"
    result = container_split(basic_input, sep='|')
    assert result[0] == basic_input.split(sep='|') and result[1] == True

def test_split_w_nested_string():

    basic_input = "arg0   arg1 arg2='fred, phyllis, and phillip'"
    result = container_split(basic_input)
    assert result[0] == ["arg0", "arg1", "arg2='fred, phyllis, and phillip'"] \
        and result[1] == True

def test_comma_split_w_nested_string():

    basic_input = "arg0, arg1, arg2='fred, phyllis, and phillip'"
    result = container_split(basic_input, sep=',')
    assert result[0] == ["arg0", " arg1", " arg2='fred, phyllis, and phillip'"] \
        and result[1] == True

def test_equals_split_w_equals_in_string():

    basic_input = "arg0='bob=0'"
    result = container_split(basic_input, sep='=')
    assert result[1] == True
    assert result[0] == ["arg0", "'bob=0'"]

def test_open_container():

    basic_input = "arg0=0 arg1=(1,"
    result = container_split(basic_input)
    print(result[0])
