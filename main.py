# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from datetime import datetime, date
from dateutil import parser
from initialize_json import compile_json
from math import log10, ceil

from db_proxy import DbConn
from random_population import generate_random_data


MAX_NUM_TESTS = 10000


# Change to use dateutil.parser
def string_to_date(s: str) -> date:
    date1 = parser(s)
    date2 = datetime.strptime(s, '%Y-%m-%d').date()
    if date1 == date2:
        return date1
    print(f'{date1=} != {date2=}')
    exit(0)


def get_num_tests(num_tests: int) -> int:
    if num_tests < 0:
        num_tests = -num_tests
    if num_tests > MAX_NUM_TESTS:
        num_tests = MAX_NUM_TESTS


def get_padded_string(i: int, num_tests: int) -> str:
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


def load_VP_data_format(filename):
    inception_not_found = True
    population = {}
    last_population_seen = 0
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            data = line.split(',')
            if len(data) != 2:
                print(f'cannot process line number: {i+1} \"line\"')
                continue

            d = string_to_date(data[0])
            if d is None:
                print(f'skip {line=}')
                continue
            pop = int(data[1])
            if inception_not_found and pop > 0:
                inception_not_found = False
            if inception_not_found:
                continue
            last_population_seen += pop
            population[d] = last_population_seen
    return population


def load_data(filename):
    population = {}
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            data = line.split(',')
            if len(data) != 2:
                print(f'cannot process line number: {i+1} \"line\"')
                continue
            d = string_to_date(data[0])
            if d is None:
                print(f'skip {line=}')
                continue
            population[d] = int(data[1])
    return population


def load_data_set(data_file, vp_format):
    if vp_format:
        return load_VP_data_format(data_file)
    return load_data(data_file)


def write_population_to_file(population, filename: str) -> None:
    with open('file_name', 'w') as f:
        for d in population:
            f.write(f'{d},{population[d]}\n')


num_tests = 10000
num_tests = 1


def main() -> int:
    i = 0
    mild_errors = 0
    big_errors = 0
    huge_errors = 0
    while(i < num_tests):
        population = generate_random_data(.1, 2.5)
        start = list(population.keys())[0]
        s_dic = DbConn.to_initialization_string(population)
        padding = get_padded_string(i, num_tests)
        company_name = 'company_' + padding
        employer_json = compile_json(company_name, start, Schedule.QUARTERLY, s_dic)
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

    print(f'Mild Errors: {mild_errors} out of {i} tests')
    print(f'Big Errors: {big_errors} out of {i} tests')
    print(f'Huge Errors: {huge_errors} out of {i} tests')
    return 0


if __name__ == "__main__":
    main()
