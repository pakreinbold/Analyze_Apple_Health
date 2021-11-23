import datetime as dt
import numpy as np
import pandas as pd
from ..fitness_processing import convert_elevation, convert_temp, convert_hum, enforce_dtypes


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


def test_enforce_dtypes():
    ''' Make sure that dtypes are converted properly '''
    runs = pd.DataFrame({'Date': ['11/11/2011', '11/11/2021'],
                         'Start': ['11:11', '11:11'],
                         'End': ['12:12', '12:12']})
    heart_rates = pd.DataFrame({'Time': ['2021/11/11 11:11:00']})

    # Check heart rates
    rns = enforce_dtypes(runs, mode='runs')
    assert rns['Date'].dtype == dt.date
    assert rns['Start'].dtype == dt.time
    assert rns['End'].dtype == dt.time

    # Check runs
    hrs = enforce_dtypes(heart_rates, mode='heart_rates')
    assert hrs['Time'].dtype in [np.dtype('<M8[ns]'), dt.datetime]

    # General checks
    try:
        enforce_dtypes(pd.DataFrame(), mode='yeet')
    except ValueError:
        assert True
