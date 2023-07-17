# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date
from pydantic import BaseModel
from typing import Optional
from math import ceil
import json


class Substance(BaseModel):
    name: str
    percent: float

    # This is a period based set of data
    # The inital estimates for a period about to start are calculated and stored here:
    period_apriori_estimate: Optional[list[float]]

    # After the fact we can get the actual required number of tests:
    period_aposteriori_truth: Optional[list[float]]

    period_overcount_error: Optional[list[float]]

    # The ints are the values that are prescribed each period
    period_apriori_required_tests_predicted: Optional[list[int]]

    def __str__(self) -> str:
        return f'{self.name=} and {self.percent=}'

    @property
    def num_periods(self) -> int:
        return len(self.period_apriori_estimate)

    def print_stats(self) -> None:
        tests_total = sum(self.period_apriori_required_tests_predicted)
        print(f'Calculated num {self.name} tests: {tests_total}')
        print('\nAll results:')
        for p in range(len(self.period_apriori_required_tests_predicted)):
            print(f'{p}: Est: {self.period_apriori_estimate[p]}, Truth: {self.period_aposteriori_truth[p]}, Req: {self.period_apriori_required_tests_predicted[p]}')

        print('')
        print(f' {self.period_aposteriori_truth=} -> {sum(self.period_aposteriori_truth)}')
        print(f'  {self.period_apriori_estimate=} -> {sum(self.period_apriori_estimate)}')
        print('')
        print(f'{self.period_apriori_required_tests_predicted=} -> {sum(self.period_apriori_required_tests_predicted)}')
        print(f'{self.period_overcount_error=} -> {sum(self.period_overcount_error)}')

    def final_overcount(self) -> int:
        return sum(self.period_apriori_required_tests_predicted) - self.tests_required

    def make_predictions(self, initial_donor_count: int, start: date, end: date, days_in_year: int) -> None:
        num_days = (end-start).days + 1
        apriori_estimate = float(num_days)*self.percent*float(initial_donor_count)/float(days_in_year)
        self.period_apriori_estimate.append(apriori_estimate)
        previous_overcount_error = sum(self.period_overcount_error) if len(self.period_overcount_error) > 0 else 0.0

        # find the lagest overcount that we can eliminate in the current period
        account_for = min(apriori_estimate, previous_overcount_error)

        tests_predicted = ceil(apriori_estimate - account_for)
        tests_predicted = max(tests_predicted, 0)
        self.period_apriori_required_tests_predicted.append(tests_predicted)

    def accept_population_data(self, donor_count_list: list, days_in_year: int) -> None:
        average_donor_count_for_period = float(sum(donor_count_list))/float(len(donor_count_list))
        average_donor_count_for_year = average_donor_count_for_period * float(len(donor_count_list))/float(days_in_year)
        aposteriori_truth = average_donor_count_for_year*self.percent
        self.period_aposteriori_truth.append(aposteriori_truth)
        tests_predicted = self.period_apriori_required_tests_predicted[-1]
        self.period_overcount_error.append(float(tests_predicted)-aposteriori_truth)

    def generate_final_report(self) -> None:
        self.print_stats()

    def population_deviation(self, p) -> float:
        return (self.period_aposteriori_truth[p] - self.period_apriori_estimate[p]) / self.period_apriori_estimate[p]

    @property
    def tests_required(self) -> int:
        return ceil(sum(self.period_aposteriori_truth))

    def generate_period_report(self) -> str:
        string = f',type:,{self.name}:\n'
        string += f',percent:,{100.0* self.percent} %\n'
        string += ',SUMMARY TABLE:\n'
        offset = ',,'
        string += ',DATA:\n'
        apriori_estimates = offset + 'Apriori estimate,'
        aposteriori_truth = offset + 'Aposteiori truth,'
        overcount_error = offset + 'Over count error,'
        population_deviation = offset + 'Pool variation (%),'
        apriori_required_tests_predicted = offset + 'prescribed # tests,'

        for p in range(self.num_periods):
            apriori_estimates += f'{self.period_apriori_estimate[p]},'
            aposteriori_truth += f'{self.period_aposteriori_truth[p]},'
            overcount_error += f'{self.period_overcount_error[p]},'
            population_deviation += f'{100.0*self.population_deviation(p)},'
            apriori_required_tests_predicted += f'{self.period_apriori_required_tests_predicted[p]},'

        string += apriori_estimates + '\n'
        string += aposteriori_truth + '\n'
        string += overcount_error + '\n'
        string += population_deviation + '\n'
        string += apriori_required_tests_predicted + '\n\n'
        string += offset + 'PRESCRIBED:,' + str(sum(self.period_apriori_required_tests_predicted)) + '\n'
        string += offset + 'NEEDED:,' + str(self.tests_required) + '\n'
        return string + '\n'


def generate_substance(json_str: str) -> Substance:
    d_dict = json.loads(json_str)
    d_dict['percent'] = float(d_dict['percent'])
    d_dict['period_apriori_estimate'] = []
    d_dict['period_aposteriori_truth'] = []
    d_dict['period_apriori_required_tests_predicted'] = []
    d_dict['period_overcount_error'] = []
    return Substance(**d_dict)
