# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date, datetime
from employer import Schedule

employer_json = {
    'name': 'company-name',
    'schedule': Schedule.QUARTERLY,
    'sub_a': '{"name": "alcohol", "percent": ".1"}',
    'sub_d': '{"name": "drug", "percent": ".5"}',

    # The rest can all be junk, as it gets overwritten in initialize
    'pop': '{"start":"2023-12-14", "pop":"200"}',
    'pool_inception': '2023-02-01',
    'start_count': '0',
    'year': 2000,
    # 'employee_count': {'2023-01-01': 100},
    'period_start_dates': ['2023-01-01'],
}


def generate_population_value(datafile: str, inception: date, start_count: int, mu: float, sigma: float) -> str:
    s_datafile = f'"datafile":\"{datafile}\"'
    s_start = f'"start":\"{inception}\"'
    s_pop = f'"pop":\"{start_count}\"'
    s_mu = f'"mu":\"{mu}\"'
    s_sigma = f'"sigma":\"{sigma}\"'
    phrase = f'{s_datafile}, {s_start}, {s_pop}, {s_mu}, {s_sigma}'
    population = '{'+phrase+'}'
    return population


def compile_json(company_name: str,
                 inception: date,
                 start_count: int,
                 schedule: Schedule = Schedule.QUARTERLY,
                 datafile: str = '',
                 mu: float = 0.0,
                 sigma: float = 0) -> dict:

    employer_json['name'] = company_name
    employer_json['schedule'] = schedule
    employer_json['pop'] = generate_population_value(datafile, inception, start_count, mu, sigma)
    employer_json['pool_inception'] = f'{inception}'
    employer_json['start_count'] = f'{start_count}'
    start = datetime.strptime(inception, '%Y-%m-%d').date()
    employer_json['year'] = start.year
    employer_json['period_start_dates'] = ['1900-01-01']

    # print(f'{employer_json=}')
    # print(f'{type(employer_json)=}')

    with open(f'{datafile}.json', 'w') as f:
        f.write('{\n')
        for item in employer_json:
            f.write(f'    {item}: {employer_json[item]},\n')
        f.write('}\n')

    return employer_json
