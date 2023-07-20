# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from datetime import date, timedelta, datetime
from random import randint
from initialize_json import compile_json
from math import log10, ceil
import random


MAX_NUM_TESTS = 10000
MAX_POP = 500
num_tests = 10000
num_tests = 1

def string_to_date(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except:
        return None

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
                inception_date = string_to_date(d)
                inception_not_found = False
            if inception_not_found:
                continue

            last_population_seen += pop
            population[d] = last_population_seen
    for d in population:
        print(f'{str(d)} -> {population[d]}')
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

def calculate_population_change(d, mu, sigma: float) -> int:
    if abs(sigma) < 0.000001:
        return 0
    if d.weekday() < 5:
        return int(random.gauss(mu, sigma))
    return 0

def order_correctly(start: date, end: date) -> tuple:
    if start > end:
        tmp = end
        end = start
        start = tmp
    return start, end

def increment(day: date) -> date:
    oneday = timedelta(days=1)
    return day+oneday

def generate_population(start: date, end: date, pop: int, mu: float = 0.0, sigma: float = 0) -> dict:
    (start, end) = order_correctly(start, end)
    pop = max(0, pop)
    population = {}
    day = start
    population[start] = pop
    while day < end:
        day = increment(day)
        pop += calculate_population_change(day, mu, sigma)
        pop = max(0, pop)
        population[day] = pop
    return population

def generate_random_data(mu: float = 0, sigma: float = 0):
    pop = get_random_population()
    start = string_to_date(get_random_date())
    end = date(year=start.year, month=12, day = 31)
    return generate_population(start, end, pop, mu, sigma)
#################################################

def write_population_to_file(population, filename: str) -> None:
    with open('file_name', 'w') as f:
        for d in population:
            f.write(f'{d},{population[d]}\n')


def main() -> int:
    i = 0
    mild_errors = 0
    big_errors = 0
    huge_errors = 0
    while(i < num_tests):
        #population = generate_random_data(.1, 2.5)
        #for d in population:
        #    print(f'{str(d)}->{population[d]}')
        #exit(0)
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
