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
    'alcohol_administered': 0,
    'drug_administered': 0,
    'year': 2000,
    'employee_count': {'2023-01-01': 100},
    'period_start_dates': ['2023-01-01']
}


num_tests = 1000


def main():
    i = 0
    errors = 0.0
    while(i < num_tests):
        e = Employer(**employer_json)
        e.start_count = randint(1, 500)
        days = randint(0, 364)
        year = 2016 + randint(0, 10)
        year_start = date(year=year, month=1, day=1) + timedelta(days=days)
        e.pool_inception = year_start + timedelta(days=days)
        e.initialize()
        # e.base_print()
        errors += e.run_test_scenario()
        i += 1

    print(f'Errors: {errors} out of {num_tests}')
    return 0
    # e.print_setup()
    # e.randomize_employee_count(0, 2)
    # e.pretty_print()


if __name__ == "__main__":
    main()
