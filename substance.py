# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date
from pydantic import BaseModel
from typing import Optional
from math import ceil, floor
import json


# EPSILON = 0.0000000000000001
EPSILON = 0.0000000001


def discretize_float(v: float, epsilon: float = EPSILON) -> float:
    sign = -1 if v < 0 else 1
    abs_v = abs(v)
    if abs_v - int(abs_v) < epsilon:
        return sign * int(abs_v)
    return v


class Substance(BaseModel):
    name: str
    percent: float

    # The ints are the values that are prescribed each period
    required_tests_predicted: Optional[list[int]]

    # After the fact we can get the actual required number of tests:
    aposteriori_truth: Optional[list[float]]

    overcount_error: Optional[list[float]]

    def __str__(self) -> str:
        return f'{self.name=} and {self.percent=}'

    # If we want to increase the periods and rerun, we can do this first
    def clear_data(self):
        self.required_tests_predicted = []
        self.aposteriori_truth = []
        self.overcount_error = []

    @property
    def actual_num_tests_required(self) -> int:
        val = sum(self.aposteriori_truth)
        return ceil(discretize_float(val))

    # Used by employer to decide if the test needs to be reported
    def final_overcount(self) -> int:
        return sum(self.required_tests_predicted) - self.actual_num_tests_required

    @property
    def previous_overcount_error(self) -> float:
        return sum(self.overcount_error) if len(self.overcount_error) > 0 else 0.0

    def make_apriori_predictions(self, initial_donor_count: int, start: date, end: date, days_in_year: int) -> None:
        num_days = (end-start).days + 1
        # best guess at average population divided by # days in the year times percent
        apriori_estimate = (float(num_days*initial_donor_count)/float(days_in_year))*self.percent

        # find the largest overcount that we can eliminate in the current period
        account_for = min(apriori_estimate, self.previous_overcount_error)

        # correct for floating point error.
        self.required_tests_predicted.append(ceil(discretize_float(apriori_estimate - account_for)))

    def determine_aposteriori_truth(self, donor_count_list: list, days_in_year: int) -> None:
        # true average population divided by # days in the year times percent
        self.aposteriori_truth.append(float(sum(donor_count_list))/float(days_in_year)*self.percent)

        # keep track of anythong we missed through the estimate
        self.overcount_error.append(float(self.required_tests_predicted[-1]) - self.aposteriori_truth[-1])

    ############################
    #  REPORT GENERATION CODE  #
    ############################
    @property
    def num_periods(self) -> int:
        return len(self.required_tests_predicted)

    @staticmethod
    def average_population_over_period(donor_list):
        return float(sum(donor_list)) / float(len(donor_list))

    def required_sum_by_period(self, period_index: int) -> int:
        required_sum = sum([self.aposteriori_truth[i] for i in range(period_index+1)])
        return ceil(discretize_float(required_sum))

    def predicted_sum_by_period(self, period_index: int) -> int:
        return sum([self.required_tests_predicted[i] for i in range(period_index+1)])

    def overcount_by_period(self, period_index: int) -> int:
        return self.predicted_sum_by_period(period_index) - self.required_sum_by_period(period_index)

    @staticmethod
    def format_to_csv(array_of_numbers):
        val = ''
        for i, p in enumerate(array_of_numbers):
            if i > 0:
                val += ','
            val += "{:8.4f}".format(float(p))
        return val

    def print_period(self, period_index: int, start_pop: int, percent_of_year: float, avg_pop: float) -> float:
        print(f'\n{sum(self.required_tests_predicted)=}')
        print(f'{ceil(discretize_float(sum(self.aposteriori_truth)))=}')
        print(f'{floor(discretize_float(sum(self.overcount_error)))=}')
        print(f'prescribed tests: {self.required_tests_predicted} (known at period start)')
        print(f'required tests : {self.aposteriori_truth} (known at period end)')
        print(f'overcount error: {self.overcount_error}')

    def print_report(self, days_in_year: int, donor_list_by_period: list[int]) -> None:
        num_periods = len(donor_list_by_period)

        print(f'\n############ {self.name} ###################')
        for p in range(num_periods):
            donor_list = donor_list_by_period[p]
            days_in_period = len(donor_list)
            start_pop = donor_list[0]
            percent_of_year = float(days_in_period)/float(days_in_year)
            avg_pop = Substance.average_population_over_period(donor_list)

            print(f'##### Period: {p} ########')
            print(f'start pop       : {start_pop} (known at period start)')
            print(f'percent of year : {percent_of_year} (known at period start)')
            print(f'average pop    : {avg_pop} (known at period end)\n')

            if p == num_periods - 1:
                self.print_period(p, start_pop, percent_of_year, avg_pop)

        final_error = floor(discretize_float(sum(self.overcount_error)))

        required = '[' + Substance.format_to_csv(self.aposteriori_truth) + ']'
        prescribed = '[' + Substance.format_to_csv(self.required_tests_predicted) + ']'
        error = '[' + Substance.format_to_csv(self.overcount_error) + ']'

        if final_error < 0:
            print(f'\n*** Under estimated required number of tests by {-final_error}')
        elif final_error < 1:
            print(f'\n*** Correct number of tests prescribed')
        else:
            print(f'\n***Over estimated required number of tests by {final_error}')

        print(f'pres = {prescribed}')
        print(f'requ = {required}')
        oc_sum = sum(self.overcount_error)
        if oc_sum < 0:
            print(f'over = {error}  <=> {oc_sum} ! UNDER COUNT' )
        elif oc_sum < 1:
            print(f'over = {error}  <=> {oc_sum}' )
        else:
            print(f'over = {error}  <=> {oc_sum}  ! OVER COUNT' )

        print(f'{self.required_tests_predicted=}')
        print(f'{self.aposteriori_truth=}')
        print(f'{self.overcount_error=}')


    ####################################################################

    def generate_period_report(self, initial_pop: list[int], avg_pop: list[float], percent_of_year: list[float]) -> str:
        string = f',type:,{self.name}:\n'
        string += f',percent:,{100.0* self.percent} %\n'
        string += ',SUMMARY TABLE:\n'
        offset = ',,'
        header = offset + 'period ->,'
        required_tests_predicted = offset + 'prescribed # tests,'
        aposteriori_truth = offset + 'Aposteriori truth,'
        overcount_error = offset + 'Over count error,'

        aposteriori_required_tests = offset + 'cum. tests required,'
        apriori_predicted_tests = offset + 'cum. tests prescribed,'
        difference = offset + 'prescribed test over-count:,'

        for p in range(self.num_periods):
            header += f'Period {p},'
            required_tests_predicted += f'{self.required_tests_predicted[p]},'
            aposteriori_truth += f'{self.aposteriori_truth[p]},'
            overcount_error += f'{self.overcount_error[p]},' + (', ***%' if p == len(initial_pop)-1 else '')

            aposteriori_required_tests += f'{self.required_sum_by_period(p)},'
            apriori_predicted_tests += f'{self.predicted_sum_by_period(p)},'
            difference += f'{self.overcount_by_period(p)},'

        string += header + '\n'
        string += required_tests_predicted + '\n'
        string += aposteriori_truth + '\n'
        string += overcount_error + '\n\n'

        string += aposteriori_required_tests + '\n'
        string += apriori_predicted_tests + '\n'
        string += difference + '\n\n'

        string += offset + 'PRESCRIBED:,' + str(sum(self.required_tests_predicted)) + '\n'
        string += offset + 'NEEDED:,' + str(self.actual_num_tests_required) + '\n'
        return string + '\n'

    def generate_final_report(self) -> None:
        tests_total = sum(self.required_tests_predicted)
        print(f'Calculated num {self.name} tests: {tests_total}')
        print('\nAll results:')
        for p in range(len(self.required_tests_predicted)):
            # print(f'{p}: Est: {self.apriori_estimate[p]}, Truth: {self.aposteriori_truth[p]}, Req: {self.required_tests_predicted[p]}')
            print(f'{p}: Est: Truth: {self.aposteriori_truth[p]}, Req: {self.required_tests_predicted[p]}')

        print('')
        print(f' {self.aposteriori_truth=} -> {sum(self.aposteriori_truth)}')
        # print(f'  {self.apriori_estimate=} -> {sum(self.apriori_estimate)}')
        print('')
        print(f'{self.required_tests_predicted=} -> {sum(self.required_tests_predicted)}')
        print(f'{self.overcount_error=} -> {sum(self.overcount_error)}')


def generate_substance(json_str: str) -> Substance:
    d_dict = json.loads(json_str)
    d_dict['percent'] = float(d_dict['percent'])
    # d_dict['apriori_estimate'] = []
    d_dict['aposteriori_truth'] = []
    d_dict['required_tests_predicted'] = []
    d_dict['overcount_error'] = []
    return Substance(**d_dict)
