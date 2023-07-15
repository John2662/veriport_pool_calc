# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
from math import ceil, floor
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

    # These get auto filled in the initialize method
    period_estimates: Optional[list[float]]
    period_actual: Optional[list[float]]
    accumulating_error: Optional[list[float]]

    # The ints are the values that are prescribed each period
    period_sample_size: Optional[list[int]]

    def initialize(self):
        self.period_estimates = []
        self.period_actual = []
        self.period_sample_size = []
        self.accumulating_error = []

    def __str__(self):
        return f'{self.name=} and {self.percent=}'

    @staticmethod
    def generate_object(json_str):
        d_dict = json.loads(json_str)
        d_dict['percent'] = float(d_dict['percent'])
        d_dict['period_estimates'] = [0.0]
        d_dict['period_actual'] = [0.0]
        d_dict['period_sample_size'] = [0]
        d_dict['accumulating_error'] = [0.0]
        return Substance(**d_dict)

    def print_stats(self, owner):
        tests_total = sum(self.period_sample_size)
        print(f'{self.name} results:')
        for p in range(len(self.period_sample_size)):
            print(f'{p}: E: {self.period_estimates[p]}, A: {self.period_actual[p]}, S:{self.period_sample_size[p]}')

        print(f'Total {self.name} tests   : {tests_total}')
        #print(f'Expected alcohol tests: {self.guess_at_alcohol}')
        print(f'     {self.period_actual=} -> {sum(self.period_actual)}')
        print(f'  {self.period_estimates=} -> {sum(self.period_estimates)}')
        print(f'{self.period_sample_size=} -> {sum(self.period_sample_size)}')



class Employer(BaseModel):
    start_count: int
    pool_inception: date
    schedule: Schedule = Schedule.QUARTERLY

    sub_d: str  # Optional[Substance]
    sub_a: str  # Optional[Substance]

    # These get auto filled in the initialize method
    year: Optional[int]
    employee_count: Optional[dict]
    period_start_dates: Optional[list[date]]

    @property
    def alcohol_percent(self):
        return self._al.percent

    @property
    def drug_percent(self):
        return self._dr.percent

    @property
    def num_periods(self):
        return len(self.period_start_dates)

    @property
    def final_period(self):
        return len(self.period_start_dates)-1

    @property
    def last_day_of_year(self):
        return self.pool_inception.replace(month=12, day=31)

    @property
    def total_days_in_year(self):
        return calendar.isleap(self.year) + 365

    @property
    def fraction_of_year(self):
        #print(f'{self.last_day_of_year=}')
        #print(f'{self.pool_inception=}')
        #print(1+(self.last_day_of_year-self.pool_inception).days)
        return float(1+(self.last_day_of_year-self.pool_inception).days) / float(self.total_days_in_year)

    @property
    def guess_at_alcohol(self):
        return ceil(self.fraction_of_year*self.start_count*self.alcohol_percent)

    @property
    def guess_at_drug(self):
        return ceil(self.fraction_of_year*self.start_count*self.drug_percent)

    @staticmethod
    def order_correctly(start, end):
        if start > end:
            tmp = end
            end = start
            start = tmp
        return start, end

    # INITIALIZATION METHODS
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

        # Not sure if I want this "special" date added or not....
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

        self._dr = Substance.generate_object(self.sub_d)
        self._dr.initialize()
        self._al = Substance.generate_object(self.sub_a)
        self._al.initialize()

    def initialize_employee_count(self):
        start_date = self.pool_inception
        end_date = self.pool_inception.replace(month=12, day=31)
        delta = timedelta(days=1)
        while(start_date <= end_date):
            self.employee_count[start_date] = self.start_count
            start_date += delta

    def initialize(self, custom_period_start_dates=[]):
        self.year = self.pool_inception.year
        self.employee_count = {}
        self.initialize_employee_count()

        self.period_start_dates = []
        self.initialize_periods(custom_period_start_dates)

    def period_end_date(self, period_index):
        if period_index == len(self.period_start_dates)-1:
            return self.last_day_of_year
        return (self.period_start_dates[period_index+1]-timedelta(days=1))


    def base_print(self):
        print(f'Num employees  : {self.start_count}')
        print(f'Inception date : {self.pool_inception}')
        print(f'Fractional year: {self.fraction_of_year}')
        print('#########')
        for p in range(self.num_periods):
            start = self.period_start_dates[p]
            end = self.period_end_date(p)
            days = (end-start).days+1
            employ_weight = self.start_count * float(days)/float(self.total_days_in_year)
            print(f'{p}->[{start} to {end}] has {days} days and {employ_weight}. A: {self.alcohol_percent * employ_weight}, D: {self.drug_percent * employ_weight}')
        print(f'Employee Density : {self.fraction_of_year*self.start_count}')
        print(f'Expected drug    : {self.guess_at_drug}')
        print(f'Expected alcoho  : {self.guess_at_alcohol}')
        print('')

    @staticmethod
    def get_count_change(d, mu, sigma):
        if d.weekday() < 5:
            return int(random.gauss(mu, sigma))
        return 0

    #  TODO: change to randomize next period
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

    def record_previous_error(self, period_index):
        if period_index < 0:
            print('ERROR 1')
            exit(0)
        if period_index > self.final_period:
            print('ERROR 2')
            exit(0)
            period_index = self.final_period

        drug_tests_asserted = self._dr.period_sample_size[period_index]
        alcohol_tests_asserted = self._al.period_sample_size[period_index]

        drug_tests_needed = self._dr.period_actual[period_index]
        alcohol_tests_needed = self._al.period_actual[period_index]

        d_error = float(drug_tests_asserted)-drug_tests_needed
        a_error = float(alcohol_tests_asserted) - alcohol_tests_needed

        #print(f'{d_error=}')
        #print(f'{a_error=}')

        self._dr.accumulating_error.append(d_error)
        self._al.accumulating_error.append(a_error)

        #print(f'** {self._al.accumulating_error=}')
        #print(f'** {self._dr.accumulating_error=}')
        return

    def calculate_estimates(self, period_index, start, end):
        #print(f'\nIN calculate_estimates: {period_index=}')
        fraction_of_year = (float(Employer.day_count(start, end))/float(self.total_days_in_year))
        employee_density = fraction_of_year * self.employee_count[start]
        period_drug_estimate = employee_density*self.drug_percent
        period_alcohol_estimate = employee_density*self.alcohol_percent

        self._dr.period_estimates.append(period_drug_estimate)
        self._al.period_estimates.append(period_alcohol_estimate)

        # This is a hureistic!!!
        if self.employee_count[start] > 100:
            candidate_drug = ceil(period_drug_estimate)
            candidate_alcohol = ceil(period_alcohol_estimate)
        elif self.employee_count[start] > 30:
            candidate_drug = round(period_drug_estimate)
            candidate_alcohol = round(period_alcohol_estimate)
        else:
            candidate_drug = floor(period_drug_estimate)
            candidate_alcohol = floor(period_alcohol_estimate)

        return candidate_drug, candidate_alcohol

    def fix_sample_size(self, period_index, candidate_drug, candidate_alcohol):
        if period_index > 0:
            self.record_previous_error(period_index-1)

        if period_index == self.final_period:
            candidate_drug -= sum(self._dr.accumulating_error)
            candidate_alcohol -= sum(self._al.accumulating_error)

        # This is a hureistic!!!
        # start = self.period_start_dates[period_index]
        # if self.employee_count[start] > 100:
        #     candidate_drug = ceil(candidate_drug)
        #     candidate_alcohol = ceil(candidate_alcohol)
        # elif self.employee_count[start] > 30:
        #     candidate_drug = round(candidate_drug)
        #     candidate_alcohol = round(candidate_alcohol)
        # else:
        #     candidate_drug = floor(candidate_drug)
        #     candidate_alcohol = floor(candidate_alcohol)

        if candidate_drug < 0:
            candidate_drug = 0

        if candidate_alcohol < 0:
            candidate_alcohol = 0

        candidate_drug = ceil(candidate_drug)
        candidate_alcohol = ceil(candidate_alcohol)

        self._al.period_sample_size.append(candidate_alcohol)
        self._dr.period_sample_size.append(candidate_drug)


    def calculate_true_values(self, period_index, start, end):
        fraction_of_year = (float(Employer.day_count(start, end))/float(self.total_days_in_year))
        employee_average = 0
        day = start
        day_count = 0
        while day <= end:
            employee_average += self.employee_count[day]
            day_count += 1
            day += timedelta(days=1)

        employee_density = fraction_of_year * (float(employee_average)/float(day_count))

        self._dr.period_actual.append(employee_density*self.drug_percent)
        self._al.period_actual.append(employee_density*self.alcohol_percent)


    def randomize_period(self, period_index, start, end, mu, sigma):
        pass

    def print_alcohol_stats(self, period_index):
        alcohol_tests_total = sum(self._al.period_sample_size)

        print('\n$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        self.base_print()

        print('\nAlcohol results:')
        for p in range(period_index):
            print(f'{p}: A-e: {self._al.period_estimates[p]}, A-a: {self._al.period_actual[p]}, A-s:{self._al.period_sample_size[p]}')

        print(f'Total alcohol tests   : {alcohol_tests_total}')
        print(f'Expected alcohol tests: {self.guess_at_alcohol}')
        print(f'     {self._al.period_actual=} -> {sum(self._al.period_actual)}')
        print(f'  {self._al.period_estimates=} -> {sum(self._al.period_estimates)}')
        print(f'{self._al.period_sample_size=} -> {sum(self._al.period_sample_size)}')

    def print_drug_stats(self, period_index):
        drug_tests_total = sum(self._dr.period_sample_size)

        print('\n$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        self.base_print()

        print('Drug results:')
        for p in range(period_index):
            print(f'{p}: D-e: {self._dr.period_estimates[p]}, D-a: {self._dr.period_actual[p]}, D-s:{self._dr.period_sample_size[p]}')

        print(f'Total drug tests   : {drug_tests_total}')
        print(f'Expected drug tests: {self.guess_at_drug}')
        print(f'        {self._dr.period_actual=} -> {sum(self._dr.period_actual)}')
        print(f'     {self._dr.period_estimates=} -> {sum(self._dr.period_estimates)}')
        print(f'   {self._dr.period_sample_size=} -> {sum(self._dr.period_sample_size)}')

    def report_errors(self, period_index, final_start, final_end):
        drug_tests_total = 0
        alcohol_tests_total = 0
        for p in range(self.num_periods):
            drug_tests_total += self._dr.period_sample_size[p]
            alcohol_tests_total += self._al.period_sample_size[p]

        d_error = abs(drug_tests_total - self.guess_at_drug)
        a_error = abs(alcohol_tests_total - self.guess_at_alcohol)

        if d_error >= 3 or a_error >= 3:
            if d_error >= 3:
                self.print_drug_stats(self.final_period)
            if a_error >= 3:
                self.print_alcohol_stats(self.final_period)
            return 3

        if d_error >= 2 or a_error >= 2:
            if d_error >= 2:
                self.print_drug_stats(self.final_period)
            if a_error >= 2:
                self.print_alcohol_stats(self.final_period)
            return 2

        if d_error >= 1 or a_error >= 1:
            if d_error >= 1:
                self.print_drug_stats(self.final_period)
            if a_error >= 1:
                self.print_alcohol_stats(self.final_period)
            return 1

        return 0



    def period_start_end(self, period_index):
        return self.period_start_dates[period_index], self.period_end_date(period_index)


    def run_test_scenario(self, mu=0, sigma=2, randomize=False):

        #print('######################')
        self.initialize()
        previous_start = self.pool_inception
        previous_end = self.pool_inception
        previous_period_index = 0
        for period_index in range(len(self.period_start_dates)):
            start, end = self.period_start_end(period_index)
            candidate_drug, candidate_alcohol = self.calculate_estimates(period_index, start, end)
            if period_index > 0:
                self.calculate_true_values(previous_period_index, previous_start, previous_end)
            self.fix_sample_size(period_index, candidate_drug, candidate_alcohol)
            if randomize:
                self.randomize_period(period_index, start, end, mu, sigma)
            previous_period_index = period_index
            previous_start = start
            previous_end = end
        self.calculate_true_values(previous_period_index, previous_start, previous_end)
        return self.report_errors(previous_period_index, previous_start, previous_end)
