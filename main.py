# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Employer, Schedule
# import json
from datetime import date, timedelta

from random import randint

employer_json = {
    'start_count': '7',
    'pool_inception': '2023-02-01',
    'alcohol_percent': .1,
    'drug_percent': .5,
    'schedule': Schedule.QUARTERLY,
    # The rest can all be junk, as it gets overwritten in initialize
    'year': 2000,
    'employee_count': {'2023-01-01': 100},
    'period_start_dates': ['2023-01-01'],
    'period_alcohol_estimates': [0.0],
    'period_drug_estimates': [0.0],
    'period_alcohol_actual': [0.0],
    'period_drug_actual': [0.0],
    'period_alcohol_sample_size': [0],
    'period_drug_sample_size': [0],
    'accumulating_alcohol_error': [0.0],
    'accumulating_drug_error': [0.0]
}


num_tests = 10000
#num_tests = 1


def main():
    i = 0
    mild_errors = 0
    big_errors = 0
    huge_errors = 0
    while(i < num_tests):
        e = Employer(**employer_json)
        e.start_count = randint(1, 500)
        days = randint(0, 364)
        year = 2016 + randint(0, 10)
        year_start = date(year=year, month=1, day=1) + timedelta(days=days)
        e.pool_inception = year_start + timedelta(days=days)
        #e.schedule = Schedule.MONTHLY

        #lock it down for debug
        #e.pool_inception = date(year=2018, month=2, day=14)
        #e.start_count = 4
        e.initialize()
        err = e.run_test_scenario2()
        if err >= 3:
            huge_errors += 1
        elif err >= 2:
            big_errors += 1
        elif err == 1:
            mild_errors += 1
        i += 1

    print(f'Mild Errors: {mild_errors} out of {num_tests}')
    print(f'Big Errors: {big_errors} out of {num_tests}')
    print(f'Huge Errors: {huge_errors} out of {num_tests}')
    return 0

if __name__ == "__main__":
    main()
