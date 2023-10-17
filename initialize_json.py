# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date

RUN_FROM_VERIPORT = False

if RUN_FROM_VERIPORT:
    from .employer import Schedule, Employer
else:
    from employer import Schedule, Employer


def get_period_start_dates(inception: date, schedule: Schedule) -> list[date]:
    sd = Employer.initialize_period_start_dates(inception, schedule)
    sd_str = []
    for d in sd:
        sd_str.append(str(d))
    return sd_str


def compile_substance_str(name: str, percent: float, disallow: int) -> str:
    n = f'\"name\": \"{name}\"'
    p = f'\"percent\": \"{str(percent)}\"'
    d = f'\"disallow_zero_chance\": \"{str(disallow)}\"'
    return '{' + n + ', ' + p + ', ' + d + '}'


def compile_json(inception: date,
                 schedule: Schedule,
                 disallow_zero_chance: int,
                 dr_percent: float,
                 al_percent: float) -> dict:
    employer_json = {}
    employer_json['schedule'] = schedule
    employer_json['pool_inception'] = f'{inception}'
    employer_json['period_start_dates'] = get_period_start_dates(inception, schedule)
    employer_json['sub_d'] = compile_substance_str('drug', dr_percent, disallow_zero_chance)
    employer_json['sub_a'] = compile_substance_str('alcohol', al_percent, disallow_zero_chance)
    return employer_json
