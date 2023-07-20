# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from datetime import date, timedelta
from random import randint
from initialize_json import compile_json
from math import log10, ceil


MAX_NUM_TESTS = 10000
MAX_POP = 500
num_tests = 10000
num_tests = 1


def get_random_date(year: int = 0, month: int = 0, day: int = 0) -> str:
    if year > 1900 and month > 0 and month <= 12 and day > 0 and day <= 31:
        return str(date(year=year, month=month, day=day))
    days = randint(0, 364)
    year = 2016 + randint(0, 10)
    return str(date(year=year, month=1, day=1) + timedelta(days=days))


def get_random_population(pop: int = 0) -> int:
    if pop <= 0:
        return randint(1, MAX_POP)
    return pop


def get_num_tests(num_tests: int) -> int:
    if num_tests < 0:
        num_tests = -num_tests
    if num_tests > MAX_NUM_TESTS:
        num_tests = MAX_NUM_TESTS


def get_padded_string(i: int, num_tests: int) -> str:
    return ''
    places = ceil(log10(num_tests))-1

    if i < 10:
        return '_' * places + str(i)
    if i < 100:
        return '_' * (places-1) + str(i)
    if i < 1000:
        return '_' * (places-2) + str(i)
    if i < 10000:
        return '_' * (places-3) + str(i)
    if i < 100000:
        return '_' * (places-4) + str(i)
    return str(i)


def main() -> int:
    i = 0
    mild_errors = 0
    big_errors = 0
    huge_errors = 0
    while(i < num_tests):
        pop = get_random_population()
        start = get_random_date()
        mu = 0.0001  # will drift up slowly
        mu = -0.0001  # will drift down slowly
        mu = 0.01
        sigma = 1
        # pop = get_random_population(438)
        # start = get_random_date(2026, 4, 26)
        # mu = 0
        # sigma = 0
        pad = get_padded_string(i, num_tests)
        datafile = f'run_output/company_{pad}_input'
        employer_json = compile_json(f'run_output/company_{pad}_output', start, pop, Schedule.QUARTERLY, datafile, mu, sigma)

        print(f'{start=}')
        e = Employer(**employer_json)
        err = e.run_test_scenario(2)

        if err >= 3:
            huge_errors += 1
        elif err >= 2:
            big_errors += 1
        elif err == 1:
            mild_errors += 1
        i += 1
        if err > 0:
            break

        mu += .1

    print(f'{mu=}')
    print(f'{sigma=}')
    print(f'Mild Errors: {mild_errors} out of {i} tests')
    print(f'Big Errors: {big_errors} out of {i} tests')
    print(f'Huge Errors: {huge_errors} out of {i} tests')
    return 0


if __name__ == "__main__":
    main()
