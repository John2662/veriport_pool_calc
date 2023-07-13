# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
# import calendar
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

    # These get auto filled:
    alcohol_administered: int
    drug_administered: int
    year: Optional[int]
    employee_count: Optional[dict]
    period_start_dates: Optional[list[date]]

    def initialize(self, custom_period_start_dates=[]):
        self.year = self.pool_inception.year
        self.employee_count = {}
        self.alcohol_administered = 0
        self.drug_administered = 0
        start_date = self.pool_inception
        end_date = self.pool_inception.replace(month=12, day=31)
        delta = timedelta(days=1)
        while(start_date <= end_date):
            self.employee_count[start_date] = self.start_count
            start_date += delta

        if self.schedule == Schedule.MONTHLY:
            self.period_start_dates = []
            for m in range(12):
                month = m+1
                # day = calendar.monthrange(self.year, month)[1]
                date = self.pool_inception.replace(month=month, day=1)
                if date < self.pool_inception:
                    continue
                self.period_start_dates.append(date)

        elif self.schedule == Schedule.QUARTERLY:
            self.period_start_dates = []
            for m in range(4):
                month = 3*m+1
                # day = calendar.monthrange(self.year, month)[1]
                date = self.pool_inception.replace(month=month, day=1)
                if date < self.pool_inception:
                    continue
                # If the pool inception is in th emiddle of a period, we need to get
                #  that as the start of the 1st period
                if date > self.pool_inception and len(self.period_start_dates) == 0:
                    self.period_start_dates.append(self.pool_inception)
                self.period_start_dates.append(date)

            # Not sure if I wan this "special" date added or not....
            # self.period_start_dates.append(self.pool_inception.replace(month=12, day=1))

        else:
            self.period_start_dates = custom_period_start_dates

        print(f'{self.days_in_year()=}')
        for c, d in enumerate(self.period_start_dates):
            print(f'{c}->{d}')
        print('And Now:')
        for d in self.employee_count:
            period_index = self.get_current_period_index(d)
            # print(f'{d} -> period {period_index}')
            print(f'{d} -> period {period_index} starting {self.period_start_dates[period_index]} is on {self.period_bounds(d)} and has {self.days_in_current_period(d)}')
        exit(0)

    @staticmethod
    def get_count_change(d, mu, sigma):
        if d.weekday() < 5:
            return int(random.gauss(mu, sigma))
        return 0

    def randomize_employee_count(self, mu, sigma):
        curr_count = self.start_count
        weight = 0
        for d in self.employee_count:
            curr_count += weight
            self.employee_count[d] = curr_count
            weight = Employer.get_count_change(d, mu, sigma)

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

    def year_end(self):
        return self.pool_inception.replace(month=12, day=31)

    def days_in_year(self):
        return (self.year_end() - self.pool_inception).days + 1

    def get_current_period_index(self, curr_date):
        if curr_date.year != self.year:
            return -1
        for c, d in enumerate(self.period_start_dates):
            if c == len(self.period_start_dates)-1:
                return c
            if curr_date >= d and curr_date < self.period_start_dates[c+1]:
                return c
        return -2

    def period_end_date(self, period_index):
        if period_index == len(self.period_start_dates)-1:
            return self.year_end()
        return (self.period_start_dates[period_index+1]-timedelta(days=1))

    def days_in_current_period(self, curr_date):
        period_index = self.get_current_period_index(curr_date)
        return 1+(self.period_end_date(period_index)-self.period_start_dates[period_index]).days

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
        return (self.period_start_dates[-1], self.year_end())

    def apriori_projections(self):
        pass

    def aposteriori_corrections(self):
        pass

    def integrate_over_year(self):
        pass

    def measure_accuracy(self):
        pass

    def run_scenario(self, mu=0, sigma=2):
        self.initialize()
        self.randomize_employee_count(mu, sigma)
