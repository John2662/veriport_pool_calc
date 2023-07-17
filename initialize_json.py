# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date
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
    'employee_count': {'2023-01-01': 100},
    'period_start_dates': ['2023-01-01'],
}


def generate_population_value(inception: date, start_count: int, mu: float, sigma: int):
    s_start = f'"start":\"{inception}\"'
    s_pop = f'"pop":\"{start_count}\"'
    s_mu = f'"mu":\"{mu}\"'
    s_sigma = f'"sigma":\"{sigma}\"'
    phrase = f'{s_start}, {s_pop}, {s_mu}, {s_sigma}'
    population = '{'+phrase+'}'
    return population


def compile_json(company_name: str,
                 inception: date,
                 start_count: int,
                 schedule: Schedule = Schedule.QUARTERLY,
                 datafile: str = '',
                 mu: float = 0.0,
                 sigma: int = 0):

    employer_json['name'] = company_name
    employer_json['schedule'] = schedule
    employer_json['pop'] = generate_population_value(inception, start_count, mu, sigma)

    return employer_json