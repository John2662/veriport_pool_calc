# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date
from employer import Schedule, TpaEmployer


def get_period_start_dates(inception: date, schedule: Schedule) -> list[date]:
    sd = TpaEmployer.initialize_period_start_dates(inception, schedule)
    sd_str = []
    for d in sd:
        sd_str.append(str(d))
    return sd_str


def compile_json(inception: date,
                 schedule: Schedule) -> dict:
    employer_json = {}
    employer_json['schedule'] = schedule
    employer_json['pool_inception'] = f'{inception}'
    employer_json['period_start_dates'] = get_period_start_dates(inception, schedule)
    employer_json['sub_d'] = '{"name": "drug", "percent": ".5"}'
    employer_json['sub_a'] = '{"name": "alcohol", "percent": ".1"}'
    return employer_json
