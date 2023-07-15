# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
from math import ceil
import calendar
from enum import Enum
from pydantic import BaseModel
from typing import Optional
import json

import random


class Schedule(Enum):
    MONTHLY = 12
    QUARTERLY = 4
    CUSTOM = 0


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

    def __str__(self):
        return f'{self.name=} and {self.percent=}'

    @staticmethod
    def generate_object(json_str):
        d_dict = json.loads(json_str)
        d_dict['percent'] = float(d_dict['percent'])
        d_dict['period_apriori_estimate'] = []
        d_dict['period_aposteriori_truth'] = []
        d_dict['period_apriori_required_tests_predicted'] = []
        d_dict['period_overcount_error'] = []
        return Substance(**d_dict)

    def print_stats(self, owner):
        tests_total = sum(self.period_apriori_required_tests_predicted)
        print(f'Predicted  num {self.name} tests: {owner.guess_for(self.name)}')
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

    def final_overcount(self):
        return self.period_overcount_error[-1] if len(self.period_overcount_error) > 0 else 0.0

    def make_predictions(self, initial_donor_count, start, end, days_in_year):
        num_days = (end-start).days + 1
        apriori_estimate = float(num_days)*self.percent*float(initial_donor_count)/float(days_in_year)
        self.period_apriori_estimate.append(apriori_estimate)
        previous_overcount_error = sum(self.period_overcount_error) if len(self.period_overcount_error) > 0 else 0.0

        # find the lagest over count that we can work off in the period
        account_for = min(apriori_estimate, previous_overcount_error)

        tests_predicted = ceil(apriori_estimate - account_for)
        tests_predicted = max(tests_predicted, 0)
        self.period_apriori_required_tests_predicted.append(tests_predicted)

    def accept_population_data(self, donor_count_list, days_in_year):
        average_donor_count_for_period = float(sum(donor_count_list))/float(len(donor_count_list))
        average_donor_count_for_year = average_donor_count_for_period * float(len(donor_count_list))/float(days_in_year)
        aposteriori_truth = average_donor_count_for_year*self.percent
        self.period_aposteriori_truth.append(aposteriori_truth)
        tests_predicted = self.period_apriori_required_tests_predicted[-1]
        self.period_overcount_error.append(float(tests_predicted)-aposteriori_truth)

    def generate_final_report(self, owner):
        self.print_stats(owner)


class Employer(BaseModel):
    start_count: int
    pool_inception: date
    schedule: Schedule = Schedule.QUARTERLY
    sub_d: str
    sub_a: str

    # These get auto filled in the initialize method
    year: Optional[int]
    employee_count: Optional[dict]
    period_start_dates: Optional[list[date]]

    @property
    def num_periods(self):
        return len(self.period_start_dates)

    # @property
    # def final_period(self):
    #     return len(self.period_start_dates)-1

    @property
    def last_day_of_year(self):
        return self.pool_inception.replace(month=12, day=31)

    @property
    def total_days_in_year(self):
        return calendar.isleap(self.year) + 365

    @property
    def fraction_of_year(self):
        return float(1+(self.last_day_of_year-self.pool_inception).days) / float(self.total_days_in_year)

    @property
    def alcohol_percent(self):
        return self._al.percent

    @property
    def drug_percent(self):
        return self._dr.percent

    def guess_for(self, type):
        if type == 'drug':
            return ceil(self.fraction_of_year*self.start_count*self.drug_percent)
        return ceil(self.fraction_of_year*self.start_count*self.alcohol_percent)

    @staticmethod
    def order_correctly(start, end):
        if start > end:
            tmp = end
            end = start
            start = tmp
        return start, end

    def initialize_monthly_periods(self):
        self.period_start_dates.append(self.pool_inception)
        for m in range(12):
            month = m+1
            date = self.pool_inception.replace(month=month, day=1)
            if date <= self.pool_inception:
                continue
            self.period_start_dates.append(date)

    def initialize_quarterly_periods(self):
        self.period_start_dates.append(self.pool_inception)
        for m in range(4):
            month = 3*m+1
            date = self.pool_inception.replace(month=month, day=1)
            if date <= self.pool_inception:
                continue
            self.period_start_dates.append(date)

        dec_1 = self.pool_inception.replace(month=12, day=1)
        if self.pool_inception < dec_1:
            self.period_start_dates.append(dec_1)

    def initialize_custom_periods(self, custom_period_start_dates):
        self.period_start_dates = custom_period_start_dates

    def initialize_periods(self, custom_period_start_dates):
        if self.schedule == Schedule.MONTHLY:
            self.initialize_monthly_periods()
        elif self.schedule == Schedule.QUARTERLY:
            self.initialize_quarterly_periods()
        else:
            self.initialize_custom_periods(custom_period_start_dates)

    def initialize_employee_count(self, mu, sigma, randomize):
        start_date = self.pool_inception
        end_date = self.pool_inception.replace(month=12, day=31)
        delta = timedelta(days=1)
        while(start_date <= end_date):
            self.employee_count[start_date] = self.start_count
            start_date += delta

    def initialize(self, custom_period_start_dates=[], mu=0, sigma=2, randomize=False):
        self.year = self.pool_inception.year
        self.employee_count = {}
        self.initialize_employee_count(mu, sigma, randomize)
        self.period_start_dates = []
        self.initialize_periods(custom_period_start_dates)
        self._dr = Substance.generate_object(self.sub_d)
        self._al = Substance.generate_object(self.sub_a)

    def period_end_date(self, period_index):
        if period_index == len(self.period_start_dates)-1:
            return self.last_day_of_year
        return (self.period_start_dates[period_index+1]-timedelta(days=1))

    def base_print(self):
        print(f'Num employees  : {self.start_count}')
        print(f'Inception date : {self.pool_inception}')
        print(f'Fractional year: {self.fraction_of_year}')
        for p in range(self.num_periods):
            start = self.period_start_dates[p]
            end = self.period_end_date(p)
            days = (end-start).days+1
            print(f'{p}->[{start} to {end}] has {days} days')
        print(f'Expected drug    : {self.guess_for("drug")}')
        print(f'Expected alcoho  : {self.guess_for("alcohol")}')
        print('')

    @staticmethod
    def get_count_change(d, mu, sigma):
        if d.weekday() < 5:
            return int(random.gauss(mu, sigma))
        return 0

    def randomize_employee_count(self, period, mu, sigma):
        return
        curr_count = self.start_count
        weight = 0
        for d in self.employee_count:
            curr_count += weight
            self.employee_count[d] = curr_count
            weight = Employer.get_count_change(d, mu, sigma)

    @staticmethod
    def day_count(start, end):
        return (end-start).days + 1

    def period_start_end(self, period_index):
        return self.period_start_dates[period_index], self.period_end_date(period_index)

    def load_period_donors(self, start, end):
        period_donor_count_list = []
        day = start
        day_count = 0
        while day <= end:
            period_donor_count_list.append(self.employee_count[day])
            day_count += 1
            day += timedelta(days=1)
        return period_donor_count_list

    def run_test_scenario(self, mu=0, sigma=2, randomize=False):
        self.initialize(mu, sigma, randomize)
        for period_index in range(len(self.period_start_dates)):
            start, end = self.period_start_end(period_index)
            self._al.make_predictions(self.employee_count[start], start, end, self.total_days_in_year)
            self._dr.make_predictions(self.employee_count[start], start, end, self.total_days_in_year)
            period_donor_count_list = self.load_period_donors(start, end)
            self._al.accept_population_data(period_donor_count_list, self.total_days_in_year)
            self._dr.accept_population_data(period_donor_count_list, self.total_days_in_year)
        if self._dr.final_overcount() > 1 or self._al.final_overcount() > 1:
            self.base_print()
            print('\n*********************************************\n')
            self._al.generate_final_report(self)
            print('\n*********************************************\n')
            self._dr.generate_final_report(self)
            exit(0)
            return 1
        return 0
