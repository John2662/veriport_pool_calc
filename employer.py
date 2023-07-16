# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
from pydantic import BaseModel
from typing import Optional
from math import ceil
import calendar
from enum import Enum

from db_proxy import DbConn
from substance import Substance


class Schedule(Enum):
    MONTHLY = 12
    QUARTERLY = 4
    CUSTOM = 0


class Employer(BaseModel):
    name: str
    schedule: Schedule = Schedule.QUARTERLY

    # These are used to load ancillary data
    sub_d: str
    sub_a: str
    pop: str

    # These get auto filled in the initialize method
    start_count: int
    pool_inception: date
    year: Optional[int]
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

    def initialize(self, custom_period_start_dates=[], mu=0, sigma=2, randomize=False):
        self.year = self.pool_inception.year
        # self.employee_count = {}
        # self.initialize_employee_count(mu, sigma, randomize)
        self.period_start_dates = []
        self.initialize_periods(custom_period_start_dates)
        self._dr = Substance.generate_object(self.sub_d)
        self._al = Substance.generate_object(self.sub_a)
        self._db_conn, self.pool_inception, self.start_count = DbConn.generate_object(self.pop)
        print(f'{self._db_conn=}')

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
    def day_count(start, end):
        return (end-start).days + 1

    def period_start_end(self, period_index):
        return self.period_start_dates[period_index], self.period_end_date(period_index)

    def load_period_donors(self, start, end):
        period_donor_count_list = []
        day = start
        day_count = 0
        while day <= end:
            period_donor_count_list.append(self._db_conn.employee_count(day))
            day_count += 1
            day += timedelta(days=1)
        return period_donor_count_list

    def write_csv_report(self):
        with open(f'{self.name}.csv', 'w') as f:
            for d in self._db_conn.population:
                if d in self.period_start_dates:
                    f.write('\nPeriod start\n')
                f.write(f'{d},{self._db_conn.employee_count(d)}\n')

    def run_test_scenario(self, mu=0, sigma=2, randomize=False):
        self.initialize(mu, sigma, randomize)
        for period_index in range(len(self.period_start_dates)):
            start, end = self.period_start_end(period_index)
            self._al.make_predictions(self._db_conn.employee_count(start), start, end, self.total_days_in_year)
            self._dr.make_predictions(self._db_conn.employee_count(start), start, end, self.total_days_in_year)
            period_donor_count_list = self.load_period_donors(start, end)
            self._al.accept_population_data(period_donor_count_list, self.total_days_in_year)
            self._dr.accept_population_data(period_donor_count_list, self.total_days_in_year)

        self.write_csv_report()

        if self._dr.final_overcount() > 1 or self._al.final_overcount() > 1:
            self.base_print()
            print('\n*********************************************\n')
            self._al.generate_final_report(self)
            print('\n*********************************************\n')
            self._dr.generate_final_report(self)
            exit(0)
            return 1
        return 0

# TODO:
# 1. read input employee data as csv
# 2. write csv report
# 3. turn on "randomization" and debug if needed
# 4. Calculate "area variation" for changing employee data
