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

import random


class Schedule(Enum):
    MONTHLY = 12
    QUARTERLY = 4
    CUSTOM = 0


class Employer(BaseModel):
    start_count: int
    pool_inception: date
    alcohol_percent: float
    drug_percent: float
    schedule: Schedule = Schedule.QUARTERLY

    # These get auto filled in the initialize method
    alcohol_administered: int
    drug_administered: int
    year: Optional[int]
    employee_count: Optional[dict]
    period_start_dates: Optional[list[date]]

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
        return float((self.last_day_of_year-self.pool_inception).days) / float(self.total_days_in_year)

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

        # Not sure if I want this "special" date added or not....
        dec_1 = self.pool_inception.replace(month=12, day=1)
        if self.pool_inception < dec_1:
            self.period_start_dates.append(dec_1)

    def initialize_custom_periods(self, custom_period_start_dates):
        self.period_start_dates = custom_period_start_dates

    def initialize_periods(self, custom_period_start_dates):
        if self.schedule == Schedule.MONTHLY:
            self.iniitialize_monthly_periods()
        elif self.schedule == Schedule.QUARTERLY:
            self.initialize_quarterly_periods()
        else:
            self.initialize_custom_periods(custom_period_start_dates)

    def initialize_employee_count(self):
        start_date = self.pool_inception
        end_date = self.pool_inception.replace(month=12, day=31)
        delta = timedelta(days=1)
        while(start_date <= end_date):
            self.employee_count[start_date] = self.start_count
            start_date += delta

    def initialize(self, custom_period_start_dates=[]):
        self.year = self.pool_inception.year
        self.alcohol_administered = 0
        self.drug_administered = 0

        self.employee_count = {}
        self.initialize_employee_count()

        self.period_start_dates = []
        self.initialize_periods(custom_period_start_dates)

    def period_end_date(self, period_index):
        if period_index == len(self.period_start_dates)-1:
            return self.last_day_of_year
        return (self.period_start_dates[period_index+1]-timedelta(days=1))

    def average_employee_count_over_interval(self, start, end):
        start, end = Employer.order_correctly(start, end)
        day = start
        employee_count = 0
        while(day <= end):
            employee_count += self.employee_count[day]
            day += timedelta(days=1)
        return float(employee_count)/float(1+(end-start).days)

    def average_employee_count_till_end_of_period(self, period_index, cummulative=True):
        if cummulative:
            return self.average_employee_count_over_interval(self.pool_inception, self.period_end_date(period_index))
        return self.average_employee_count_over_interval(self.period_start_dates[period_index], self.period_end_date(period_index))

    def is_final_period(self, period_index):
        return period_index == len(self.period_start_dates)-1

    def cummulative_days_in_pool_year_to_given_day(self, current_day):
        if current_day <= self.pool_inception:
            return 0
        return 1+(current_day-self.pool_inception).days

    def calculate_intermediate_period_values(self, period_index):
        avg_cumm_employee_count = self.average_employee_count_till_end_of_period(period_index)
        cummulative_num_days = self.cummulative_days_in_pool_year_to_given_day(self.period_end_date(period_index))
        cumm_fraction_of_year = float(cummulative_num_days)/float(self.total_days_in_year)
        alcohol = ceil(avg_cumm_employee_count * cumm_fraction_of_year * self.alcohol_percent - self.alcohol_administered)
        drug = ceil(avg_cumm_employee_count * cumm_fraction_of_year * self.drug_percent - self.drug_administered)
        return drug, alcohol

    def calculate_final_period_values(self):
        return self.calculate_intermediate_period_values(self.final_period)

    def apriori_projections(self, period_index):
        period_bound = len(self.period_start_dates)
        if period_index < 0 or period_index >= period_bound:
            print(f'Attempting to calculate period {period_index} which is not in (0,...{period_bound})')
            exit(0)

        if self.is_final_period(period_index):
            drug, alcohol = self.calculate_final_period_values()
        else:
            drug, alcohol = self.calculate_intermediate_period_values(period_index)

        self.alcohol_administered += alcohol
        self.drug_administered += drug

        s = '**' if self.is_final_period(period_index) else 'In'
        return f'{s} period {period_index} D: {drug}; A: {alcohol}'

    def total_administered(self, projections):
        num_drug = ceil(self.start_count * self.drug_percent * self.fraction_of_year)
        num_alco = ceil(self.start_count * self.alcohol_percent * self.fraction_of_year)

        if num_drug != self.drug_administered or num_alco != self.alcohol_administered:
            if abs(num_drug - self.drug_administered) > 1 or abs(num_alco - self.alcohol_administered) > 1:
                print('\n########################################')
                self.base_print()
                for p in projections:
                    print(p)
                print(f'In total    D: {self.drug_administered}; A: {self.alcohol_administered}')

                if num_drug != self.drug_administered and num_alco != self.alcohol_administered:
                    print(f'Expected    D: {num_drug}; A: {num_alco}')
                if num_drug != self.drug_administered and num_alco == self.alcohol_administered:
                    print(f'Expected    D: {num_drug}; A: --')
                if num_drug == self.drug_administered and num_alco != self.alcohol_administered:
                    print(f'Expected    D: --; A: {num_alco}')
                print('########################################\n')
                return 1.00000001
            else:
                return 1.0
        return 0.0

    def base_print(self):
        print(f'Num employees  : {self.start_count}')
        print(f'Inception date : {self.pool_inception}')
        print(f'Fractional year: {self.fraction_of_year}')
        print('')

    def aposteriori_corrections(self):
        pass

    def run_test_scenario(self, mu=0, sigma=2):
        self.initialize()

        projections = []
        for period_index in range(len(self.period_start_dates)):
            projections.append(self.apriori_projections(period_index))
            self.randomize_employee_count(period_index, mu, sigma)
        return self.total_administered(projections)

    # These methods are just used for testing
    def measure_accuracy(self):
        pass

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

    # THESE METHODS ARE NOT REALLY NEEDED
    def period_bounds(self, given_day):
        if given_day < self.period_start_dates[0]:
            return (date(year=self.year-1, month=1, day=1), date(year=self.year-1, month=12, day=31))
        if given_day.year > self.year:
            return (date(year=self.year+1, month=1, day=1), date(year=self.year+1, month=12, day=31))
        stop = len(self.period_start_dates)-1
        i = 0
        while i < stop:
            if given_day < self.period_start_dates[i+1]:
                return (self.period_start_dates[i], self.period_end_date(i))
            i += 1
        return (self.period_start_dates[-1], self.last_day_of_year)

    def pretty_print(self):
        print(f'start count = {self.start_count}')
        print(f'inception   = {self.pool_inception}')
        print(f'year        = {self.year}')
        print('Employee count:')
        for d in self.employee_count:
            if d.day == 1:
                print('')
            if d in self.period_start_dates:
                print(f'##### {d} #####')
            print(f'  {d}->{self.employee_count[d]} in period {self.period_bounds(d)}')

    # def total_days_in_pool_year(self):
    #     return (self.last_day_of_year - self.pool_inception).days + 1

    def period_index_for_given_day(self, curr_date):
        if curr_date.year != self.year:
            return -1
        for c, d in enumerate(self.period_start_dates):
            if c == len(self.period_start_dates)-1:
                return c
            if curr_date >= d and curr_date < self.period_start_dates[c+1]:
                return c
        return -2

    def days_in_current_period(self, curr_date):
        period_index = self.period_index_for_given_day(curr_date)
        return 1+(self.period_end_date(period_index)-self.period_start_dates[period_index]).days

    def print_setup(self):
        print(f'{self.total_days_in_year=}')
        for c, d in enumerate(self.period_start_dates):
            print(f'{c}->{d}')
        print('And Now:')
        for d in self.employee_count:
            period_index = self.period_index_for_given_day(d)
            # print(f'{d} -> period {period_index}')
            print(f'{d} -> period {period_index} starting {self.period_start_dates[period_index]} is on {self.period_bounds(d)} and has {self.days_in_current_period(d)}')
