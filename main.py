# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from initialize_json import compile_json
from math import log10, ceil
import argparse

from random_population import generate_random_population_data
from file_io import load_population_from_natural_file
from file_io import load_population_from_vp_file
from file_io import write_population_to_vp_file

MAX_NUM_TESTS = 10000


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


def get_args() -> argparse.Namespace:
    # parser = argparse.ArgumentParser(description='Process some integers.')
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',
    #                     help='an integer for the accumulator')
    # parser.add_argument('--sum', dest='accumulate', action='store_const',
    #                     const=sum, default=max,
    #                     help='sum the integers (default: find the max)')
    # args = parser.parse_args()
    # print(args.accumulate(args.integers))
    parser = argparse.ArgumentParser(description='Arguments: file_to_load, vp_format, output_directory')
    parser.add_argument('--file', type=str, help='data file to load')
    parser.add_argument('--dir', type=str, help='output directory')
    parser.add_argument('--sch', type=str, help='the testing schedule (MONTHLY, QUARTERLY, etc.)', default='quarterly')
    parser.add_argument('--vp', type=bool, help='Whether this comes from VP or from this program', default=False)
    parser.add_argument('--iter', type=int, help='number of random iterations', default=10)
    args = parser.parse_args()
    return args


def tokenize_string(s: str, t: str = '\n') -> list[str]:
    return s.split(t)


def store_data(text: str, csv: str, pop: dict, html: str, file_name: str = '', directory: str = 'run_output') -> None:
    csv = tokenize_string(csv)
    for line in csv:
        print(line)
    # TODO write to file

    text = tokenize_string(text)
    for line in text:
        print(line)
    # TODO write to file

    html = tokenize_string(html)
    with open('foo.html', 'w') as f:
        for line in html:
            f.write(line+'\n')

    # write_population_to_natural_file(pop, filename)
    # TODO get the file name figured out


def load_data_set_from_file(data_file: str, vp_format: bool, schedule: Schedule) -> tuple:
    filename = 'tmp_vp.csv'
    if vp_format:
        population = load_population_from_vp_file(data_file)
    else:
        population = load_population_from_natural_file(data_file)
        write_population_to_vp_file(population, filename)
    start = list(population.keys())[0]
    employer_json = compile_json(start, schedule, filename)
    return (Employer(**employer_json), population)


def generate_data_set_randomly(run_count: int, num_tests: int, schedule: Schedule,  mu: float, sigma: float) -> tuple:
    filename = 'tmp_vp.csv'
    population = generate_random_population_data(mu, sigma)
    write_population_to_vp_file(population, filename)
    start = list(population.keys())[0]
    employer_json = compile_json(start, schedule, filename)
    return (Employer(**employer_json), population)


def run_from_file(filename: str, vp_format: bool, schedule: Schedule) -> int:
    (e, population) = load_data_set_from_file(filename, vp_format, schedule)
    (err, csv, text, html) = e.run_test_scenario()
    if err >= 1:
        store_data(text, csv, population, html)
        print(f'hit error of level {err}')
    return err


def run_from_random_data(i: int, num_tests: int, schedule: Schedule, mu: float, sigma: float) -> int:
    (e, population) = generate_data_set_randomly(i, num_tests, schedule, .1, 2.5)
    (err, csv, text, html) = e.run_test_scenario()
    if err >= 1:
        store_data(text, csv, population, html)
        print(f'hit error of level {err}')
    return err


def from_string_to_schedule(s):
    s = s.strip().lower()
    print(f' PROCESS {s=}')
    if s == 'semimonthly':
        return Schedule.SEMIMONTHLY
    if s == 'monthly':
        return Schedule.MONTHLY
    if s == 'bimonthly':
        return Schedule.BIMONTHLY
    if s == 'quarterly':
        return Schedule.QUARTERLY
    if s == 'semiannually':
        return Schedule.SEMIANNUALLY
    if s == 'annually':
        return Schedule.ANNUALLY
    print('hit default')
    return Schedule.QUARTERLY


def main() -> int:
    args = get_args()

    schedule = from_string_to_schedule(args.sch)

    filename = args.file
    if filename is not None:
        return run_from_file(filename, args.vp, schedule)

    i = 0
    errors = {}
    num_tests = min(args.iter, MAX_NUM_TESTS)
    mu = .1
    sigma = 2.5
    while(i < num_tests):
        err = run_from_random_data(i, num_tests, schedule, mu, sigma)
        if err >= 1:
            if err not in errors:
                errors[err] = 0
            errors[err] += 1
        i += 1

    for e in errors:
        print(f'hit {errors[e]} errors of level {e} out of {num_tests}')
    return 0


if __name__ == "__main__":
    main()
