# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from datetime import datetime, date, timedelta
from dateutil.parser import parse
# from dateutil.parser import ParseError
# from dateutil.parser._parser import ParseError
from initialize_json import compile_json
from math import log10, ceil
import argparse

from db_proxy import DbConn
from random_population import generate_random_population_data


MAX_NUM_TESTS = 10000


# Change to use dateutil.parser
def string_to_date(s: str) -> date:
    try:
        date1 = parse(s).date()
    # except ParseError:
    except:
        return None

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
        return (None, None)
    return (d, pop)


def write_population_to_natural_file(population, filename: str) -> None:
    with open('file_name', 'w') as f:
        for d in population:
            f.write(f'{d},{population[d]}\n')


def load_population_from_vp_file(filename: str) -> dict:
    inception_not_found = True
    population = {}
    last_population_seen = 0
    last_date_processed = date(year=1900, month=1, day=1)
    year = 1900
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            (d, pop) = process_line(line, i)
            if d is None:
                print(f'cannot process line number: {i+1} \"{line}\"')
                continue
            if year == 1900:
                year = d.year
                print(f'{year=}')
            elif year != d.year:
                print(f'{filename} spans multiple years')
                exit(0)

            if inception_not_found and pop >= 0:
                inception_not_found = False
                last_date_processed = d
                # print(f'Inception: {str(d)} -> {pop=}')
            if inception_not_found:
                continue

            # pad out any missing dates with the last population seen
            while last_date_processed < d:
                population[last_date_processed] = last_population_seen
                last_date_processed += timedelta(days=1)

            last_date_processed = d
            last_population_seen += pop
            population[last_date_processed] = last_population_seen

    # Now pad out to the end of the year
    year_end = date(year, month=12, day=31)
    while last_date_processed <= year_end:
        population[last_date_processed] = last_population_seen
        last_date_processed += timedelta(days=1)
    return population


def load_population_from_natural_file(filename: str) -> dict:
    population = {}
    year = 1900
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            (d, pop) = process_line(line, i)
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


def load_data_set_from_file(data_file: str, vp_format: bool) -> tuple:
    if vp_format:
        population = load_population_from_vp_file(data_file)
    else:
        population = load_population_from_natural_file(data_file)
    start = list(population.keys())[0]
    s_dic = DbConn.to_initialization_string(population)
    employer_json = compile_json(start, Schedule.QUARTERLY, s_dic)
    return (Employer(**employer_json), population)


def generate_data_set_randomly(run_count: int, num_tests: int, mu: float, sigma: float) -> tuple:
    population = generate_random_population_data(mu, sigma)
    start = list(population.keys())[0]
    s_dic = DbConn.to_initialization_string(population)
    employer_json = compile_json(start, Schedule.QUARTERLY, s_dic)
    return (Employer(**employer_json), population)


def run_from_file(filename: str, vp_format: bool) -> int:
    (e, population) = load_data_set_from_file(filename, vp_format)
    (err, csv, text, html) = e.run_test_scenario()
    if err >= 1:
        store_data(text, csv, population, html)
        print(f'hit error of level {err}')
    return err


def run_from_random_data(i: int, num_tests: int, mu: float, sigma: float) -> int:
    (e, population) = generate_data_set_randomly(i, num_tests, .1, 2.5)
    (err, csv, text, html) = e.run_test_scenario()
    if err >= 1:
        store_data(text, csv, population, html)
        print(f'hit error of level {err}')
    return err


def main() -> int:
    args = get_args()

    filename = args.file
    if filename is not None:
        return run_from_file(filename, args.vp)

    i = 0
    errors = {}
    num_tests = min(args.iter, MAX_NUM_TESTS)
    mu = .1
    sigma = 2.5
    while(i < num_tests):
        err = run_from_random_data(i, num_tests, mu, sigma)
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
