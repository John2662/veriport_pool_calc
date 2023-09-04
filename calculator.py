# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, September 2023


from datetime import timedelta, date
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
                 schedule: Schedule,
                 to_depricate__vp_file: str):

        self.population = population

        # print('\nIn Calculator:')
        # print(f'\n{population=}')
        # print(f'\n{inception=}')
        # print(f'\n{schedule=}')

        # initialize the employer
        employer_json = compile_json(inception, schedule, to_depricate__vp_file)
        # print(f'\n{employer_json=}')

        self.employer = TpaEmployer(**employer_json)
        self.employer.initialize()

        # print(f'{self.employer=}')

    # Next write the interface that hides all the calls to employer in the old code
    # Once we have that we can remove the employer from everywhere except here,
    # and we can remove the DbConn object all together.
    # That that point, we just need to give this class the actual veriport
    # object that allows it to query the DB

    def make_html_report(self):
        return self.employer.make_html_report()

    def make_estimates_and_return_data_to_persist(self, period_index: int) -> tuple:
        return self.employer.make_estimates_and_return_data_to_persist(period_index)

    def load_persisted_data_and_do_period_calculations(self, period_index: int, tmp_dr_json: str, tmp_al_json: str) -> None:
        return self.employer.load_persisted_data_and_do_period_calculations(period_index, tmp_dr_json, tmp_al_json)

    # These functions fetch the data we need from the DB

    # The first function that will retrieve data from the DB
    def get_population_report(self, start: date, end: date) -> list[int]:
        requested_population = []
        while start <= end:
            requested_population.append(self.employee_count(start))
            start += timedelta(days=1)
        return requested_population

    # The second function that will retrieve data from the DB
    def employee_count(self, day: date) -> int:
        return self.population[day]

    # Check validity of the data from the DB
    def population_valid(self, start: date, end: date) -> bool:
        population = self.get_population_report(start, end)
        for d in population:
            if population[d] < 0:
                print(f'On {str(d)} population is {population[d]} < 0')
                return False
        return True
