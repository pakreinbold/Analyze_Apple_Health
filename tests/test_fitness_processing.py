import numpy as np
from ..fitness_processing import convert_elevation, convert_temp, convert_hum


def test_convert_elevation():
    ''' Make sure that an elevation string gets converted to a float properly'''
    # Case when input is a string
    res = convert_elevation('120 cm')
    assert np.abs(res - 25.4) < 1e-10

    # Case when input is a float already
    res = convert_elevation(10)
    assert res == 10


def test_convert_temp():
    ''' Make sure that a string containing the temparature is converted properly '''

    # Case when input is a string
    assert np.abs(convert_temp('10 degF') - 10) < 1e-10

    # Case when input is already a float
    assert convert_temp(10) == 10


def test_convert_hum():
    ''' Make sure the string containing humidity is converted properly '''

    # Case when input is a string
    assert np.abs(convert_hum('5000 %') - 50) < 1e-10

    # Case when input is already a float
    assert convert_hum(50) == 50
