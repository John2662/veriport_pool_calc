# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, September 2023


from employer import Employer
from data_persist import DataPersist
from initialize_json import compile_json


class Calculator:

    def __init__(self, data_persist: DataPersist):

        self.data_persist = data_persist

        # initialize the employer
        employer_json = compile_json(self.data_persist.inception, self.data_persist.schedule)

        self.employer = Employer(**employer_json)
        self.employer.initialize(self.data_persist.population)

    @property
    def pool_inception(self):
        return self.data_persist.inception

    @property
    def schedule(self):
        return self.data_persist.schedule

    def period_start_estimates(self, period_index: int, data_persist: DataPersist) -> None:
        (dr_tmp_json, al_tmp_json) = self.employer.make_estimates_and_return_data_to_persist(period_index)
        data_persist.persist_json(dr_tmp_json, 'tmp_dr.json')
        data_persist.persist_json(al_tmp_json, 'tmp_al.json')

    def period_end_calculations(self, period_index: int, data_persist: DataPersist) -> None:
        tmp_dr_json = data_persist.retrieve_json('tmp_dr.json')
        tmp_al_json = data_persist.retrieve_json('tmp_al.json')
        return self.employer.load_persisted_data_and_do_period_calculations(period_index, tmp_dr_json, tmp_al_json)

    def process_period(self, period_index: int, data_persist: DataPersist) -> None:
        if period_index == 0:
            self.period_start_estimates(period_index, data_persist)
        if period_index == data_persist.final_period_index()+1:
            score = self.period_end_calculations(period_index-1, data_persist)
            data_persist.store_reports(self.employer.make_html_report())
            return score
        if period_index > 0 and period_index <= data_persist.final_period_index():
            self.period_end_calculations(period_index-1, data_persist)
            self.period_start_estimates(period_index, data_persist)
            return 0
        return 0

    # These are the methods that we need to give the output to Veriport
    def get_requirements(self, period_index: int, drug: bool) -> int:
        if drug:
            return self.employer._dr.required_tests_predicted[period_index]
        return self.employer._al.required_tests_predicted[period_index]


def get_calculator_instance(data_persist) -> Calculator:
    return Calculator(data_persist)
