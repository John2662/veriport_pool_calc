# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from datetime import datetime, date, timedelta
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


def process_line(line: str, i: int) -> tuple:
    data = line.split(',')
    if len(data) != 2:
        print(f'cannot process line number: {i+1} \"line\"')
        return [None, None]
    d = string_to_date(data[0])
    try:
        pop = int(data[1])
    except ValueError:
        return (None, pop)
    return (d, pop)


def load_VP_data_format(filename: str) -> dict:
    inception_not_found = True
    population = {}
    last_population_seen = 0
    last_date_processed = date(year=1900, month=1, day=1)
    year = 1900
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            (d, pop) = process_line(line)
            if d is None:
                print(f'cannot process line number: {i+1} \"{line}\"')
                continue
            if year == 1900:
                year = d.year
            elif year != d.year:
                print(f'{filename} spans multiple years')
                exit(0)

            if inception_not_found and pop > 0:
                inception_not_found = False
                last_date_processed = d
            if inception_not_found:
                continue
            # pad out any missing dates
            while last_date_processed <= d:
                population[last_date_processed] = last_population_seen
                last_date_processed += timedelta(days=1)
            last_population_seen += pop
    # Now pad out to the end of the year
    year_end = date(year, month=12, day=31)
    while last_date_processed <= year_end:
        population[last_date_processed] = last_population_seen
        last_date_processed += timedelta(days=1)
    return population


def read_data_from_file(filename: str) -> dict:
    population = {}
    year = 1900
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            (d, pop) = process_line(line)
            if d is None:
                print(f'cannot process line number: {i+1} \"{line}\"')
                continue
            if year == 1900:
                year = d.year
            elif year != d.year:
                print(f'{filename} spans multiple years')
                exit(0)
            population[d] = pop
    return population


def load_data_set(data_file: str, vp_format: bool) -> dict:
    if vp_format:
        return load_VP_data_format(data_file)
    return read_data_from_file(data_file)


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
