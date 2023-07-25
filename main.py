# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from initialize_json import compile_json
# from math import log10, ceil
import argparse
import os

from random_population import generate_random_population_data
from file_io import load_population_from_natural_file
from file_io import load_population_from_vp_file
from file_io import write_population_to_vp_file
from file_io import write_population_to_natural_file

# This is valid for the length of the run, then removed in main()
TMP_POP_FILE = 'tmp_pop.csv'
MAX_NUM_TESTS = 500


def tokenize_string(s: str, t: str = '\n') -> list[str]:
    return s.split(t)


def store_data(pop: dict, html: str, directory: os.path = 'run_output', file_name: str = '') -> None:
    outfile = os.path.join(directory, f'{file_name}')
    write_population_to_natural_file(pop, f'{outfile}_nat.csv')
    write_population_to_vp_file(pop, f'{outfile}_vp.csv')
    html = tokenize_string(html)
    with open(f'{outfile}.html', 'w') as f:
        for line in html:
            f.write(line+'\n')


def population_dict_from_file(datafile: str, vp_format: bool) -> dict:
    if vp_format:
        return load_population_from_vp_file(datafile)
    else:
        return load_population_from_natural_file(datafile)


def population_dict_from_rand(mu: float, sigma: float) -> dict:
    return generate_random_population_data(mu, sigma)


def construct_employer(population: dict, schedule: Schedule) -> Employer:
    start = list(population.keys())[0]
    filename = TMP_POP_FILE
    write_population_to_vp_file(population, filename)
    employer_json = compile_json(start, schedule, filename)
    return Employer(**employer_json)


def process_data(schedule: Schedule, population: dict) -> int:
    employer = construct_employer(population, schedule)
    return employer.run_test_scenario()


def from_string_to_schedule(s):
    s = s.strip().lower()
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
    print('hit default: QUARTERLY')
    return Schedule.QUARTERLY


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
    parser.add_argument('--dir', type=str, help='output directory', default='test_out')
    parser.add_argument('--sch', type=str, help='the testing schedule (MONTHLY, QUARTERLY, etc.)', default='quarterly')
    parser.add_argument('--vp', type=bool, help='Whether this comes from VP or from this program', default=True)
    parser.add_argument('--iter', type=int, help='number of random iterations', default=4)
    args = parser.parse_args()
    return args


def base_file_name_from_path(filepath: str) -> str:
    split_filepath = filepath.split('/')
    just_file_name = os.path.splitext(split_filepath[-1])[0]
    return just_file_name


def main() -> int:
    args = get_args()

    schedule = from_string_to_schedule(args.sch)
    standard_schedule_str = Schedule.as_str(schedule)
    filename = args.file
    output = os.path.join(args.dir)
    os.makedirs(output, exist_ok=True)

    if filename is not None:
        if not os.path.isfile(filename):
            print(f'Cannot open {filename}')
            return 0
        base_file_name = base_file_name_from_path(filename)
        base_file_name += f'_{standard_schedule_str}'

        population = population_dict_from_file(filename, args.vp)
        (err, html) = process_data(schedule, population)
        final_dir = os.path.join(output, base_file_name)
        os.makedirs(final_dir, exist_ok=True)
        store_data(population, html, final_dir, base_file_name)
        print(f'hit error of level {err}')
        os.remove(TMP_POP_FILE)
        return err

    output = os.path.join(args.dir, 'random_trials')
    os.makedirs(output, exist_ok=True)

    i = 0
    errors = {}
    num_tests = min(args.iter, MAX_NUM_TESTS)
    mu = .1
    sigma = 2.5
    while(i < num_tests):
        population = population_dict_from_rand(mu, sigma)
        (err, html) = process_data(schedule, population)

        if err not in errors:
            errors[err] = 0
        errors[err] += 1

        output_err = os.path.join(output, f'err_{err}')
        os.makedirs(output_err, exist_ok=True)
        basefilename = f'results_{i}'
        basefilename += f'_{standard_schedule_str}'
        out_dir = os.path.join(output_err, f'run_{i}')
        os.makedirs(out_dir, exist_ok=True)
        store_data(population, html, out_dir, basefilename)
        i += 1

    for e in errors:
        print(f'hit {errors[e]} errors of level {e} out of {num_tests}')

    os.remove(TMP_POP_FILE)
    return 0


if __name__ == "__main__":
    main()
