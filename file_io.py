# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date, timedelta
from dateutil.parser import parse
# from dateutil.parser import ParseError
# from dateutil.parser._parser import ParseError
import argparse


# TODO: figure out how to get rid of the bare except
def string_to_date(s: str) -> date:
    try:
        return parse(s).date()
    # except ParseError:
    except:
        return None


def population_valid(population) -> bool:
    for d in population:
        if population[d] < 0:
            print(f'On {str(d)} population is {population[d]} < 0')
            return False
    return True


def process_line(line: str, i: int) -> tuple:
    data = line.split(',')
    if len(data) != 2:
        # print(f'cannot process line number: {i+1} \"line\"')
        return [None, None]
    d = string_to_date(data[0])
    try:
        pop = int(data[1])
    except ValueError:
        return (None, None)
    return (d, pop)


def load_population_from_vp_line_array(lines: list) -> dict:
    inception_not_found = True
    population = {}
    last_population_seen = 0
    last_date_processed = date(year=1900, month=1, day=1)
    year = 1900
    for i, line in enumerate(lines):
        (d, pop) = process_line(line, i)
        if d is None:
            # print(f'cannot process line number: {i+1} \"{line}\"')
            continue
        if year == 1900:
            year = d.year
        elif year != d.year:
            print(f'array {lines} spans multiple years')
            exit(0)

        if inception_not_found and pop > 0:
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


def load_population_from_vp_file(filename: str) -> dict:
    with open(filename, 'r') as f:
        lines = f.readlines()
        return load_population_from_vp_line_array(lines)


def load_population_from_natural_file(filename: str) -> dict:
    population = {}
    year = 1900
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            (d, pop) = process_line(line, i)
            if d is None:
                # print(f'cannot process line number: {i+1} \"{line}\"')
                continue
            if year == 1900:
                year = d.year
            elif year != d.year:
                print(f'{filename} spans multiple years')
                exit(0)
            population[d] = pop
    return population


def population_dict_from_file(datafile: str, vp_format: bool) -> dict:
    if vp_format:
        return load_population_from_vp_file(datafile)
    else:
        return load_population_from_natural_file(datafile)


def write_population_to_natural_file(population: dict, filename: str) -> None:
    with open(filename, 'w') as f:
        for d in population:
            f.write(f'{d},{population[d]}\n')


def write_population_to_vp_file(population: dict, filename: str) -> None:
    last_date_processed = list(population.keys())[0]
    last_pop_processed = population[last_date_processed]

    with open(filename, 'w') as f:
        f.write(f'{last_date_processed},{last_pop_processed}\n')
        for d in population:
            delta = population[d] - last_pop_processed
            if delta != 0:
                f.write(f'{d},{delta}\n')
                last_pop_processed += delta

    # Do a quick test to catch errors
    new_pop = load_population_from_vp_file(filename)
    if not population_valid(new_pop):
        print('ERROR:')
        print(f'{population}')
        print('became\n')
        print(f'{new_pop}')
        exit(0)


def natural_to_vp(filename: str) -> str:
    pop = load_population_from_natural_file(filename)
    new_file = f'vp_{filename}'
    write_population_to_vp_file(pop, new_file)
    return new_file


def vp_to_natural(filename: str) -> None:
    pop = load_population_from_vp_file(filename)
    new_file = f'n_{filename}'
    write_population_to_natural_file(pop, new_file)
    return new_file


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Arguments: file path to write to, vp_format, mu, sigma'
        )
    parser.add_argument(
        '--fp',
        type=str,
        help='filepath for input file'
        )
    parser.add_argument(
        '--vp',
        type=str,
        help='Whether to read in VP or native format',
        default='false'
        )
    args = parser.parse_args()
    return args


def main() -> int:
    args = get_args()
    print(f'{args.vp=}')
    vp = True if args.vp.lower()[0] == 't' else False
    filename = args.fp
    if vp:
        print(f'vp -> n with {filename}')
        new_filename = vp_to_natural(filename)
        print(f'n -> vp with {new_filename}')
        natural_to_vp(new_filename)
    else:
        print(f'n -> vp with {filename}')
        new_filename = natural_to_vp(filename)
        print(f'vp -> n with {new_filename}')
        vp_to_natural(new_filename)


if __name__ == "__main__":
    main()
