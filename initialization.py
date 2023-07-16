# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
from employer import Schedule
from random import randint

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


def generate_ramdom_data(mu, sigma):
    pop = randint(1, 500)
    days = randint(0, 364)
    year = 2016 + randint(0, 10)
    start = str(date(year=year, month=1, day=1) + timedelta(days=days))
    s_start = f'"start":\"{start}\"'
    s_pop = f'"pop":\"{pop}\"'
    s_mu = f'"mu":\"{mu}\"'
    s_sigma = f'"sigma":\"{sigma}\"'
    phrase = f'{s_start}, {s_pop}, {s_mu}, {s_sigma}'
    population = '{'+phrase+'}'
    employer_json['pop'] = population
    return employer_json


def run_test(company_name: str,
             inception: date,
             start_count: int,
             schedule: Schedule = Schedule.QUARTERLY,
             datafile: str = '',
             mu: float = 0.0,
             sigma: int = 0):
    pass

# TODO:
# 1. read input employee data as csv
# 2. write csv report
# 3. turn on "randomization" and debug if needed
# 4. Calculate "area variation" for changing employee data
