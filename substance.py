# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date
from pydantic import BaseModel
from typing import Optional
from math import ceil
import json


# EPSILON = 0.0000000000000001
EPSILON = 0.0000000001


def reset_to_close_int(v: float, epsilon: float = EPSILON) -> float:
    sign = -1 if v < 0 else 1
    abs_v = abs(v)
    if abs_v - int(abs_v) < epsilon:
        return sign * int(abs_v)
    return v


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

    def final_overcount(self) -> int:
        return sum(self.period_apriori_required_tests_predicted) - self.tests_required

    def make_predictions(self, initial_donor_count: int, start: date, end: date, days_in_year: int) -> None:
        num_days = (end-start).days + 1
        apriori_estimate = float(num_days)*self.percent*float(initial_donor_count)/float(days_in_year)
        self.period_apriori_estimate.append(apriori_estimate)
        previous_overcount_error = sum(self.period_overcount_error) if len(self.period_overcount_error) > 0 else 0.0

        # find the lagest overcount that we can eliminate in the current period
        account_for = min(apriori_estimate, previous_overcount_error)

        # correct for floating point error.
        # For one simple test this caused a bug if epsilon = 0.00000000000000001 (or less)
        if abs(apriori_estimate - account_for) < EPSILON:
            tests_predicted = 0
        else:
            tests_predicted = ceil(reset_to_close_int(apriori_estimate - account_for))

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

    # This is only used in a report, so it is not that critical.
    # TODO: put a better safety check in
    def population_deviation(self, p: int) -> float:
        if p >= len(self.period_apriori_estimate):
            return -1000000000000000000000.0
        if self.period_apriori_estimate[p] < EPSILON:
            return 0.0
        return (self.period_aposteriori_truth[p] - self.period_apriori_estimate[p]) / self.period_apriori_estimate[p]

    @property
    def tests_required(self) -> int:
        val = sum(self.period_aposteriori_truth)
        return ceil(reset_to_close_int(val))

    def required_sum_by_period(self, period_index: int) -> int:
        required_sum = sum([self.period_aposteriori_truth[i] for i in range(period_index+1)])
        return ceil(reset_to_close_int(required_sum))

    def predicted_sum_by_period(self, period_index: int) -> int:
        return sum([self.period_apriori_required_tests_predicted[i] for i in range(period_index+1)])

    def overcount_by_period(self, period_index: int) -> int:
        return self.predicted_sum_by_period(period_index) - self.required_sum_by_period(period_index)

    def period_summary(self, period_index, initial_pop: int, avg_pop: float, percent_of_year: float, final:bool = False):
        s = [f'In period {period_index}:']
        esti = self.period_apriori_estimate[period_index]
        trut = self.period_aposteriori_truth[period_index]
        # over = self.period_overcount_error[period_index]
        # pred = self.period_apriori_required_tests_predicted[period_index]
        s.append(f',apriori estmate = {esti}, is calculated:,Initial pop={initial_pop} * fraction of year={percent_of_year} * percent tests required {self.percent}, all rounded up ')
        s.append(f',actual value = {trut}, is calculated:,Average pop={avg_pop} * fraction of year={percent_of_year} * percent tests required {self.percent} ')
        s.append(f',over count error = {ceil(esti) - trut}, is calculated:,apriori estimate rounded up: {ceil(esti)} - truth: {trut} ')
        if final:
            s[-1] += ',***!'
        var = (trut - esti) / esti if esti > EPSILON else 0.0
        s.append(f',pool size variation = {100.0 * var}%, is calculated:,(actual value: {100.0 * trut} - apriori estimate: {esti}) divided by the apriori estimate {esti} * 100 %')
        s.append(f',pool size variation added:, {self.overcount_by_period(period_index)}, tests to number actual required')
        return s

    def generate_period_report(self, initial_pop: list[int], avg_pop: list[float], percent_of_year: list[float]) -> str:
        string = f',type:,{self.name}:\n'
        string += f',percent:,{100.0* self.percent} %\n'
        string += ',SUMMARY TABLE:\n'
        offset = ',,'
        header = offset + 'period ->,'
        apriori_estimates = offset + 'Apriori estimate,'
        aposteriori_truth = offset + 'Aposteiori truth,'
        overcount_error = offset + 'Over count error,'
        population_deviation = offset + 'Pool variation (%),'
        apriori_required_tests_predicted = offset + 'prescribed # tests,'
        aposteriori_required_tests = offset + 'cum. tests required,'
        apriori_predicted_tests = offset + 'cum. tests prescribed,'
        difference = offset + 'prescribed test over-count:,'

        for p in range(self.num_periods):
            header += f'Period {p},'
            apriori_estimates += f'{self.period_apriori_estimate[p]},'
            aposteriori_truth += f'{self.period_aposteriori_truth[p]},'
            overcount_error += f'{self.period_overcount_error[p]},' + (', ***%' if p == len(initial_pop)-1 else '')
            population_deviation += f'{100.0*reset_to_close_int(self.population_deviation(p))},'
            apriori_required_tests_predicted += f'{self.period_apriori_required_tests_predicted[p]},'
            required_sum = self.required_sum_by_period(p)
            predicted_sum = self.predicted_sum_by_period(p)

            aposteriori_required_tests += f'{required_sum},'
            apriori_predicted_tests += f'{predicted_sum},'
            difference += f'{self.overcount_by_period(p)},'

        string += header + '\n'
        string += apriori_estimates + '\n'
        string += apriori_required_tests_predicted + '\n'
        string += aposteriori_truth + '\n'
        string += overcount_error + '\n\n'
        string += population_deviation + '\n\n'
        string += apriori_predicted_tests + '\n'
        string += aposteriori_required_tests + '\n'
        string += difference + '\n\n'
        string += offset + 'PRESCRIBED:,' + str(sum(self.period_apriori_required_tests_predicted)) + '\n'
        string += offset + 'NEEDED:,' + str(self.tests_required) + '\n'
        string += offset + ','*(self.num_periods+1) + 'NOTES:' + '\n'
        for p in range(self.num_periods):
            lines = self.period_summary(p, initial_pop[p], avg_pop[p], percent_of_year[p], p == (self.num_periods-1))
            for line in lines:
                string += offset + ','*(self.num_periods+1) + line + '\n'
            string += '\n'
        return string + '\n'

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


def generate_substance(json_str: str) -> Substance:
    d_dict = json.loads(json_str)
    d_dict['percent'] = float(d_dict['percent'])
    d_dict['period_apriori_estimate'] = []
    d_dict['period_aposteriori_truth'] = []
    d_dict['period_apriori_required_tests_predicted'] = []
    d_dict['period_overcount_error'] = []
    return Substance(**d_dict)
