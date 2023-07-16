# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Employer, Schedule
from datetime import date, timedelta

from random import randint

employer_json = {
    'name': 'company-name',
    'schedule': Schedule.QUARTERLY,
    'sub_a': '{"name": "alcohol", "percent": ".1"}',
    'sub_d': '{"name": "drug", "percent": ".5"}',

    # The rest can all be junk, as it gets overwritten in initialize
    'pop': '{"start":"2023-12-14", "pop":"200"}',
    'pool_inception': '2023-02-01',
    'start_count': '0',
    'year': 2000,
    'employee_count': {'2023-01-01': 100},
    'period_start_dates': ['2023-01-01'],
}

num_tests = 1000
num_tests = 1


def generate_ramdom_data(mu, sigma):
    pop = randint(1, 500)
    days = randint(0, 364)
    year = 2016 + randint(0, 10)
    start = str(date(year=year, month=1, day=1) + timedelta(days=days))
    s_start = f'"start":\"{start}\"'
    s_pop = f'"pop":\"{pop}\"'
    s_mu = f'"mu":\"{mu}\"'
    s_sigma = f'"sigma":\"{sigma}\"'
    phrase = f'{s_start}, {s_pop}, {s_mu}, {s_sigma}'
    population = '{'+phrase+'}'
    employer_json['pop'] = population
    return employer_json


def main():
    i = 0
    mild_errors = 0
    big_errors = 0
    huge_errors = 0
    while(i < num_tests):
        mu = .1
        sigma = 2
        json_data = generate_ramdom_data(mu, sigma)
        e = Employer(**json_data)
        e.initialize()
        err = e.run_test_scenario()
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
