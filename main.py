# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule
from datetime import date, timedelta

from random import randint

from initialization import run_test

num_tests = 1000
num_tests = 1


def get_random_date():
    days = randint(0, 364)
    year = 2016 + randint(0, 10)
    return str(date(year=year, month=1, day=1) + timedelta(days=days))


def main():
    i = 0
    mild_errors = 0
    big_errors = 0
    huge_errors = 0
    while(i < num_tests):
        pop = randint(1, 500)
        start = get_random_date()
        mu = .1
        sigma = 2
        datafile = ''
        err = run_test('fake_company_name', start, pop, Schedule.QUARTERLY, datafile, mu, sigma)
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
