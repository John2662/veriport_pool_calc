# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, September 2023


from datetime import date
RUN_FROM_VERIPORT = False

if RUN_FROM_VERIPORT:
    from .employer import Employer
    from .initialize_json import compile_json
    from .schedule import Schedule
else:
    from employer import Employer
    from initialize_json import compile_json
    from schedule import Schedule


class Calculator:

    def __init__(
        self,
        schedule: Schedule,
        pool_inception: date,
        population: dict,
        disallow_zero_chance: int = 100,
        dr_fraction: float = .5,
        al_fraction: float = .1
    ):

        self.schedule = schedule
        self.pool_inception = pool_inception

        # initialize the employer
        employer_json = compile_json(self.pool_inception, self.schedule, disallow_zero_chance, dr_fraction, al_fraction)

        self.employer = Employer(**employer_json)
        self.employer.initialize(population)

    def period_end_calculations(self, period_index: int, dr_json: str, al_json: str) -> int:
        return self.employer.load_persisted_data_and_do_period_calculations(period_index, dr_json, al_json)

    def find_period_index(self, day: date) -> int:
        if day.year > self.pool_inception.year:
            return self.employer.num_periods

        if day < self.pool_inception:
            return -1

        for counter in range(self.employer.num_periods):
            period_index = self.employer.num_periods - (counter+1)
            if self.employer.period_start_dates[period_index] <= day:
                return period_index

        # This can actually never happen
        return self.employer.num_periods

    def process_period(self, period_index: int, curr_dr_json: str = '', curr_al_json: str = '') -> tuple:
        score = 0
        html = None
        (dr_json, al_json) = (curr_dr_json, curr_al_json)

        if period_index > 0:
            score = self.period_end_calculations(period_index-1, dr_json, al_json)

        if period_index == self.employer.num_periods:
            html = self.employer.make_html_report()
        else:
            self.employer.make_estimates(period_index)

        (dr_json, al_json) = self.employer.get_data_to_persist()
        return (dr_json, al_json, score, html)

    def get_requirements(self, period_index: int, drug: bool) -> int:
        if drug:
            return self.employer._dr.required_tests_predicted[period_index]
        return self.employer._al.required_tests_predicted[period_index]

    def get_debug_all_info(self, drugs=True):
        if drugs:
            return self.employer._dr.debug_all_data
        return self.employer._al.debug_all_data


def get_calculator_instance(schedule: Schedule, inception: date, population: dict) -> Calculator:
    return Calculator(schedule, inception, population)
