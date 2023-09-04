# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, September 2023


from datetime import date
from employer import Schedule, TpaEmployer
from initialize_json import compile_json


def from_int_to_schedule(i):
    if i == 24:
        return Schedule.SEMIMONTHLY
    if i == 12:
        return Schedule.MONTHLY
    if i == 6:
        return Schedule.BIMONTHLY
    if i == 4:
        return Schedule.QUARTERLY
    if i == 2:
        return Schedule.SEMIANNUALLY
    if i == 1:
        return Schedule.ANNUALLY
    print('hit default: QUARTERLY')
    return Schedule.QUARTERLY


class Calculator:

    def __init__(self,
                 population: dict,
                 inception: date,
                 schedule: Schedule):

        self.pool_inception = inception

        # initialize the employer
        employer_json = compile_json(inception, schedule)

        self.employer = TpaEmployer(**employer_json)
        self.employer.initialize(population)

    @property
    def start_count(self):
        return self.donor_count_on(self.pool_inception)

    def make_html_report(self):
        return self.employer.make_html_report()

    def donor_count_on(self, day: date) -> int:
        return self.employer.donor_count_on(day)

    def period_start_end(self, period_index: int) -> tuple:
        return self.employer.period_start_end(period_index)

    def make_estimates_and_return_data_to_persist(self, period_index: int) -> tuple:
        return self.employer.make_estimates_and_return_data_to_persist(period_index)

    def load_persisted_data_and_do_period_calculations(self, period_index: int, tmp_dr_json: str, tmp_al_json: str) -> None:
        return self.employer.load_persisted_data_and_do_period_calculations(period_index, tmp_dr_json, tmp_al_json)

    # These functions fetch the data we need from the DB

    # The first function that will retrieve data from the DB
    def get_population_report(self, start: date, end: date) -> list[int]:
        return self.employer.get_population_report(start, end)

    # The second function that will retrieve data from the DB
    def employee_count(self, day: date) -> int:
        return self.employer.employee_count(day)

    # Check validity of the data from the DB
    def population_valid(self, start: date, end: date) -> bool:
        return self.employer.population_valid(start, end)
