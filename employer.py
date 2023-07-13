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
    QUATERLY = 4
    CUSTOM = 0


employer_json = {
    'start_count': '100',
    'pool_inception': '2023-05-21',
    'alcohol_percent': .1,
    'drug_percent': .5,
    # The rest can all be junk, as it gets overwritten in initialize
    'alcohol_administered': 0,
    'drug_administered': 0,
    'year': 2000,
    'employee_count': {'2023-01-01': 100},
    'period_start_dates': ['2023-01-01']

}


class Employer(BaseModel):
    start_count: int
    pool_inception: date
    alcohol_percent: float
    drug_percent: float
    alcohol_administered: int
    drug_administered: int
    year: Optional[int]
    employee_count: Optional[dict]
    period_start_dates: Optional[list[date]]
    schedule: Schedule = Schedule.QUATERLY

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

        elif self.schedule == Schedule.QUATERLY:
            self.period_start_dates = []
            for m in range(4):
                month = 3*m+1
                # day = calendar.monthrange(self.year, month)[1]
                date = self.pool_inception.replace(month=month, day=1)
                if date < self.pool_inception:
                    continue
                self.period_start_dates.append(date)
            self.period_start_dates.append(self.pool_inception.replace(month=12, day=1))

        else:
            self.period_start_dates = custom_period_start_dates

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
            print(f'  {d}->{self.employee_count[d]}')

    def year_end(self):
        return

    # calculate year_end -
    def days_in_year(self):
        pass

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
