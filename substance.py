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
    disallow_zero_chance: int

    debug_all_data: Optional[list[str]]

    def __str__(self) -> str:
        s = f'{self.name=} and {self.percent=}\n'
        s += 'PRED:' + str(self.required_tests_predicted) + '\n'
        s += 'TRUE:' + str(self.aposteriori_truth) + '\n'
        s += 'ERROR:' + str(self.overcount_error) + '\n'
        return s

    #  If we want to increase the periods and rerun, we can do this first
    # def clear_data(self):
    #     self.required_tests_predicted = []
    #     self.aposteriori_truth = []
    #     self.overcount_error = []

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

    def random_correct_zero_tests(self, predicted_num_test: int) -> int:
        if predicted_num_test > 0:
            return predicted_num_test
        from random import randint
        random_num = randint(0, 100)
        if random_num <= self.disallow_zero_chance:
            return 1
        return 0

    def make_apriori_predictions(self, initial_donor_count: int, start: date, end: date, days_in_year: int) -> None:

        if len(self.debug_all_data) == 0:
            self.debug_all_data.append('percent,start,end,s_count,days_in_year,initial_guess,account_for,predicted,truth,oc,cum_oc')

        num_days = (end-start).days + 1
        # best guess at average population divided by # days in the year times percent
        apriori_estimate = (float(num_days*initial_donor_count)/float(days_in_year))*self.percent

        # find the largest overcount that we can eliminate in the current period
        account_for = min(apriori_estimate, self.previous_overcount_error)

        # correct for floating point error, and then add a chance to force a test even if zero are required.
        # At the start of the first period predicted_test = ceil(discretize_float(apriori_estimate))
        #   since self.previous_overcount_error is zero
        predicted_tests = self.random_correct_zero_tests(ceil(discretize_float(apriori_estimate - account_for)))
        self.required_tests_predicted.append(predicted_tests)

        self.debug_all_data.append(f'{self.percent},{str(start)},{str(end)},{initial_donor_count},{days_in_year},{apriori_estimate}, {account_for}, {predicted_tests}')

    def determine_aposteriori_truth(self, donor_count_list: list, days_in_year: int) -> None:
        # true average population divided by # days in the year times percent
        truth = float(sum(donor_count_list))/float(days_in_year)*self.percent
        self.aposteriori_truth.append(truth)

        # keep track of anything we missed through the estimate
        oc_error = float(self.required_tests_predicted[-1]) - truth
        self.overcount_error.append(oc_error)

        # At the end of the first period, this is ceil(estimate) - truth
        # self.overcount_error
        self.debug_all_data[-1] += f',{truth}, {oc_error}, {sum(self.overcount_error)}'

    def data_to_persist(self) -> str:
        return self.model_dump_json()

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

    def html_total_row(self) -> list[str]:
        r_pre = sum(self.required_tests_predicted)
        r_tru = Substance.format_float(sum(self.aposteriori_truth))
        r_err = Substance.format_float(sum(self.overcount_error))

        s = ['          <tr>\n']
        s.append('              <td>TOTAL:</td>\n')
        s.append(f'              <td>{r_pre}</td>\n')
        s.append(f'              <td>{r_tru}</td>\n')
        s.append(f'              <td>{r_err}</td>\n')
        s.append('          </tr>\n')
        return s

    def overcount_summary(self):
        final_error = floor(discretize_float(sum(self.overcount_error)))
        if final_error < 0:
            return f'  TOTAL UNDERCOUNT: {-final_error} </br> <h6> Undercount due to growing pool size </h6> </br>\n'
        elif final_error < 1:
            return '  CORRECT NUMBER OF TESTS PRESCRIBED!</br>\n'
        else:
            return f'  TOTAL OVERCOUNT: {final_error} </br> <h6> Overcount due to shrinking pool size </h6></br>\n'

    def html_period_row(self, p: int) -> list[str]:
        r_pre = self.required_tests_predicted[p]
        r_tru = Substance.format_float(self.aposteriori_truth[p])
        r_err = Substance.format_float(self.overcount_error[p])

        s = ['          <tr>\n']
        s.append(f'              <td>{p+1}</td>\n')
        s.append(f'              <td>{r_pre}</td>\n')
        s.append(f'              <td>{r_tru}</td>\n')
        s.append(f'              <td>{r_err}</td>\n')
        s.append('          </tr>\n')
        return s

    def make_html_substance_report(self) -> str:

        s = ['<div class="container">\n']
        s.append(f'  <h2>{self.name.upper()} SUMMARY:</h2>\n')
        s.append('  <table class="table table-striped">\n')
        s.append('      <thead>\n')
        s.append('          <tr>\n')
        s.append('              <th>Period</th>\n')
        s.append('              <th>Tests Prescribed</th>\n')
        s.append('              <th>Tests Required</th>\n')
        s.append('              <th>Over Count</th>\n')
        s.append('          </tr>\n')
        s.append('      </thead>\n')
        s.append('      <tbody>\n')

        for p in range(len(self.aposteriori_truth)):
            row_lines = self.html_period_row(p)
            for line in row_lines:
                s.append(line)

        row_lines = self.html_total_row()
        for line in row_lines:
            s.append(line)

        tot_pred = sum(self.required_tests_predicted)
        tot_req = ceil(discretize_float(sum(self.aposteriori_truth)))

        s.append('      </tbody>\n')
        s.append('  </table>\n')
        s.append('  <p>\n')
        s.append(f'  TOTAL  PREDICTED: {tot_pred}</br>\n')
        s.append(f'  ACTUAL REQUIRED: {tot_req}</br>\n')
        s.append(self.overcount_summary())
        s.append('  </p>\n')
        s.append('</div>\n')
        return s


def generate_substance(json_str: str) -> Substance:
    d_dict = json.loads(json_str)
    d_dict['percent'] = float(d_dict['percent'])
    d_dict['aposteriori_truth'] = []
    d_dict['required_tests_predicted'] = []
    d_dict['overcount_error'] = []
    d_dict['disallow_zero_chance'] = int(d_dict['disallow_zero_chance'])
    d_dict['debug_all_data'] = []
    return Substance(**d_dict)
