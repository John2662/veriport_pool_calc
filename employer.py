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

    @staticmethod
    def as_str(value):
        if value == Schedule.MONTHLY:
            return 'monthly'
        if value == Schedule.QUARTERLY:
            return 'quarterly'
        return 'custom'


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

    def guess_for(self, type: str):
        if type == 'drug':
            return ceil(self.fraction_of_year*self.start_count*self.drug_percent)
        return ceil(self.fraction_of_year*self.start_count*self.alcohol_percent)

    def period_end_date(self, period_index: int):
        if period_index == len(self.period_start_dates)-1:
            return self.last_day_of_year
        return (self.period_start_dates[period_index+1]-timedelta(days=1))

    ########################################
    #    VARIOUS INITIALIZATION METHODS    #
    ########################################
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

        # dec_15 = self.pool_inception.replace(month=12, day=15)
        # if self.pool_inception < dec_15:
        #     self.period_start_dates.append(dec_15)

    def initialize_custom_periods(self, custom_period_start_dates: list):
        self.period_start_dates = custom_period_start_dates

    def initialize_periods(self, custom_period_start_dates: list):
        if self.schedule == Schedule.MONTHLY:
            self.initialize_monthly_periods()
        elif self.schedule == Schedule.QUARTERLY:
            self.initialize_quarterly_periods()
        else:
            self.initialize_custom_periods(custom_period_start_dates)

    def initialize(self, custom_period_start_dates: list = []):
        self.year = self.pool_inception.year
        self.period_start_dates = []
        self.initialize_periods(custom_period_start_dates)
        self._dr = Substance.generate_object(self.sub_d)
        self._al = Substance.generate_object(self.sub_a)
        # The mu, sigma get pushed in through self.pop
        self._db_conn, self.pool_inception, self.start_count = DbConn.generate_object(self.pop)
    ########################################
    #    VARIOUS INITIALIZATION METHODS    #
    ########################################

    def load_period_donors(self, start: date, end: date):
        return self._db_conn.load_population(start, end)

    def donor_count(self, day: date):
        return self._db_conn.employee_count(day)

    def period_start_end(self, period_index: int):
        return self.period_start_dates[period_index], self.period_end_date(period_index)

    def make_period_calculations(self, period_index: int):
        start, end = self.period_start_end(period_index)
        self._al.make_predictions(self.donor_count(start), start, end, self.total_days_in_year)
        self._dr.make_predictions(self.donor_count(start), start, end, self.total_days_in_year)
        period_donor_count_list = self.load_period_donors(start, end)
        self._al.accept_population_data(period_donor_count_list, self.total_days_in_year)
        self._dr.accept_population_data(period_donor_count_list, self.total_days_in_year)

    def run_test_scenario(self):
        self.initialize()
        for period_index in range(len(self.period_start_dates)):
            self.make_period_calculations(period_index)

        self.conclude_report()
        return self._dr.final_overcount() + self._al.final_overcount()

    def conclude_report(self, output_to_screen: bool = False):
        self.write_csv()
        self.write_period_report()

        if output_to_screen and (self._dr.final_overcount() > 1 or self._al.final_overcount() > 1):
            self.base_print()
            print('\n*********************************************\n')
            self._al.generate_final_report()
            print('\n*********************************************\n')
            self._dr.generate_final_report()
            #  exit(0)

    ##############################
    #       PRINTING, REPORTS    #
    ##############################

    def write_csv(self):
        print(f'DB file: {self._db_conn.write_population_to_file()}')

        with open(f'{self.name}.csv', 'w') as f:
            period_count = 0
            for d in self._db_conn.population:
                if d in self.period_start_dates:
                    f.write(f'#,Period {period_count} start\n')
                    period_count += 1
                f.write(f'{d},{self._db_conn.employee_count(d)}\n')

    def average_pool_size(self, period_index: int):
        start = self.period_start_dates[period_index]
        end = self.period_end_date(period_index)
        return self._db_conn.average_population(start, end)

    def write_period_report(self):
        with open(f'{self.name}_summary.csv', 'w') as f:
            f.write('Company stats')
            f.write(f'Schedule:, {Schedule.as_str(self.schedule)}\n')
            f.write(f'Initial Size:, {self.start_count}\n')
            f.write(f'Number of periods:, {len(self.period_start_dates)}\n')
            f.write(', PERIOD, START DATE, AVG. POOL SIZE\n')
            for i, d in enumerate(self.period_start_dates):
                f.write(f', period {i}, {str(d)}, {str(self.average_pool_size(i))}\n')
            f.write(f'pool as % of year:, {100.0 * self.fraction_of_year}\n')
            f.write('\nApriori test predictions\n')
            f.write(f'drug % required:, {100.0*self.drug_percent}\n')
            f.write(f'inception drug expectation:, {self.guess_for("drug")}\n')
            f.write(f'alcohol % required:, {100.0*self.alcohol_percent}\n')
            f.write(f'inception alcohol expectation:, {self.guess_for("alcohol")}\n')
            f.write('\nDrug summary:\n')
            f.write(f'{self._dr.generate_period_report()}')
            f.write('\nAlcohol summary:\n')
            f.write(f'{self._al.generate_period_report()}')

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

# TODO:
# 1. read input employee data as csv
# 2. write a "driver" that pushes data in at the start of each period to mimic how it would be used in veriport
# 3. Write "heal run" function by adding more periods and rerunning
