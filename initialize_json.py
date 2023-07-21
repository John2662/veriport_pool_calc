# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date
from employer import Schedule


def compile_json(company_name: str,
                 inception: date,
                 schedule: Schedule,
                 s_dict: dict) -> dict:
    employer_json = {}
    employer_json['name'] = company_name
    employer_json['schedule'] = schedule
    employer_json['pool_inception'] = f'{inception}'
    employer_json['period_start_dates'] = ['1900-01-01']
    employer_json['sub_d'] = '{"name": "drug", "percent": ".5"}'
    employer_json['sub_a'] = '{"name": "alcohol", "percent": ".1"}'
    employer_json['db_str'] = s_dict
    return employer_json
