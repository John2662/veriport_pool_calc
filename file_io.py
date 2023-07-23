# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import datetime, date, timedelta
from dateutil.parser import parse
# from dateutil.parser import ParseError
# from dateutil.parser._parser import ParseError


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


def write_population_to_natural_file(population, filename: str) -> None:
    with open('file_name', 'w') as f:
        for d in population:
            f.write(f'{d},{population[d]}\n')


def write_population_to_vp_file(population, filename: str) -> None:
    last_date_processed = list(population.keys())[0]
    last_pop_processed = population[last_date_processed]

    with open(filename, 'w') as f:
        f.write(f'{last_date_processed},{last_pop_processed}\n')
        for d in population:
            delta = population[d] - last_pop_processed
            if delta != 0:
                f.write(f'{d},{delta}\n')
                last_pop_processed += delta


def natural_to_vp(filename):
    pass


def vp_to_natural(filename):
    pass


def main() -> int:
    pass


if __name__ == "__main__":
    main()
