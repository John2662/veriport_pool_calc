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

        # keep track of anything we missed through the estimate
        self.overcount_error.append(float(self.required_tests_predicted[-1]) - self.aposteriori_truth[-1])

    ##############################
    #    GENERATE A CSV STRING   #
    ##############################

    def generate_csv_report(self, initial_pop: list[int], avg_pop: list[float], percent_of_year: list[float]) -> str:
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

        num_periods = len(self.required_tests_predicted)
        for p in range(num_periods):
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

    ############################
    #  REPORT GENERATION CODE  #
    ############################

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
    def format_float(f):
        return "{:7.2f}".format(float(f))

    @staticmethod
    def format_to_csv(array_of_numbers, int_val: bool = False):
        val = ''
        for i, p in enumerate(array_of_numbers):
            if i > 0:
                val += ','
            val += "{:9.2f}".format(float(p))
        return val

    def make_text_substance_report(self) -> str:
        s = f'\n{self.name.upper()} SUMMARY:\n'
        r_req = Substance.format_float(sum(self.aposteriori_truth))
        required = '[' + Substance.format_to_csv(self.aposteriori_truth) + '] summed -> ' + f'{r_req}'
        r_req = Substance.format_float(sum(self.required_tests_predicted))
        prescribed = '[' + Substance.format_to_csv(self.required_tests_predicted) + '] summed -> ' + f'{r_req}'
        r_req = Substance.format_float(sum(self.overcount_error))
        error = '[' + Substance.format_to_csv(self.overcount_error) + '] summed -> ' + f'{r_req}'

        oc_sum = sum(self.overcount_error)
        s += f'   prescribed = {prescribed}\n'
        s += f'   required   = {required}\n'
        if oc_sum < 0:
            s += f'   overcount  = {error} ! UNDER COUNT by {ceil(-oc_sum)}\n\n'
        elif oc_sum < 1:
            s += f'   overcount  = {error} CORRECT PREDICTION\n\n'
        else:
            s += f'   overcount  = {error} ! OVER COUNT by {floor(oc_sum)}\n\n'

        final_error = floor(discretize_float(sum(self.overcount_error)))
        s += f'   TOTAL PREDICTED: {sum(self.required_tests_predicted)}\n'
        s += f'   TOTAL REQUIRED:  {ceil(discretize_float(sum(self.aposteriori_truth)))}\n'
        s += '   ---------------------\n'

        if final_error < 0:
            s += f'   TOTAL UNDERCOUNT: {-final_error}\n'
        elif final_error < 1:
            s += '   CORRECT NUMBER OF TESTS PRESCRIBED\n'
        else:
            s += f'   TOTAL OVERCOUNT: {final_error}\n'
        return s

    def make_html_substance_report(self) -> str:
        return ''


def generate_substance(json_str: str) -> Substance:
    d_dict = json.loads(json_str)
    d_dict['percent'] = float(d_dict['percent'])
    # d_dict['apriori_estimate'] = []
    d_dict['aposteriori_truth'] = []
    d_dict['required_tests_predicted'] = []
    d_dict['overcount_error'] = []
    return Substance(**d_dict)
