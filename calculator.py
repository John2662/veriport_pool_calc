# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, September 2023


from datetime import date
from employer import Schedule, Employer
from data_persist import DataPersist
from file_io import string_to_date
from initialize_json import compile_json


class Calculator:

    def __init__(self,
                 population: dict,
                 inception: date,
                 schedule: Schedule):

        self.pool_inception = inception

        # initialize the employer
        employer_json = compile_json(inception, schedule)

        self.employer = Employer(**employer_json)
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

    def period_start_estimates(self, period_index: int, data_persist: DataPersist) -> None:
        (dr_tmp_json, al_tmp_json) = self.make_estimates_and_return_data_to_persist(period_index)
        data_persist.persist_json(dr_tmp_json, 'tmp_dr.json')
        data_persist.persist_json(al_tmp_json, 'tmp_al.json')

    def period_end_calculations(self, period_index: int, data_persist: DataPersist) -> None:
        tmp_dr_json = data_persist.retrieve_json('tmp_dr.json')
        tmp_al_json = data_persist.retrieve_json('tmp_al.json')
        return self.load_persisted_data_and_do_period_calculations(period_index, tmp_dr_json, tmp_al_json)

    def process_period(self, period_index: int, data_persist: DataPersist) -> None:
        if period_index == 0:
            self.period_start_estimates(period_index, data_persist)
        if period_index == data_persist.final_period_index()+1:
            score = self.period_end_calculations(period_index-1, data_persist)
            data_persist.store_reports(self.make_html_report())
            return score
        if period_index > 0 and period_index <= data_persist.final_period_index():
            self.period_end_calculations(period_index-1, data_persist)
            self.period_start_estimates(period_index, data_persist)
            return 0
        return 0


def get_calculator_instance(data_persist) -> Calculator:
    # Generate a dictionary needed to construct an instance of the Calculator class
    # Hint: The json version of this is stored in the output directory of the run
    initializing_dict = data_persist.get_initializing_dict()
    inception = string_to_date(initializing_dict['pool_inception'])
    schedule = Schedule.from_int_to_schedule(int(initializing_dict['schedule']))
    return Calculator(data_persist.population, inception, schedule)
