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
from substance import generate_substance


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

    # These get auto filled in the initialize method
    pool_inception: date
    period_start_dates: Optional[list[date]]

    # These are used to load ancillary data
    sub_d: str
    sub_a: str
    db_str: str

    @property
    def start_count(self):
        return self.donor_count_on(self.pool_inception)

    @property
    def year(self):
        return self.pool_inception.year

    @property
    def num_periods(self) -> int:
        return len(self.period_start_dates)

    # @property
    # def final_period(self) -> int:
    #     return len(self.period_start_dates)-1

    @property
    def last_day_of_year(self) -> date:
        return self.pool_inception.replace(month=12, day=31)

    @property
    def total_days_in_year(self) -> int:
        return calendar.isleap(self.year) + 365

    @property
    def fraction_of_year(self) -> float:
        return float(1+(self.last_day_of_year-self.pool_inception).days) / float(self.total_days_in_year)

    @property
    def alcohol_percent(self) -> float:
        return self._al.percent

    @property
    def drug_percent(self) -> float:
        return self._dr.percent

    def guess_for(self, type: str) -> int:
        if type == 'drug':
            return ceil(self.fraction_of_year*self.start_count*self.drug_percent)
        return ceil(self.fraction_of_year*self.start_count*self.alcohol_percent)

    def period_end_date(self, period_index: int) -> int:
        if period_index == len(self.period_start_dates)-1:
            return self.last_day_of_year
        return (self.period_start_dates[period_index+1]-timedelta(days=1))

    ########################################
    #    VARIOUS INITIALIZATION METHODS    #
    ########################################
    def initialize_monthly_periods(self) -> None:
        self.period_start_dates.append(self.pool_inception)
        for m in range(12):
            month = m+1
            date = self.pool_inception.replace(month=month, day=1)
            if date <= self.pool_inception:
                continue
            self.period_start_dates.append(date)

    def initialize_quarterly_periods(self) -> None:
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

    def initialize_custom_periods(self, custom_period_start_dates: list) -> None:
        self.period_start_dates = custom_period_start_dates

    def initialize_periods(self, custom_period_start_dates: list) -> None:
        if self.schedule == Schedule.MONTHLY:
            self.initialize_monthly_periods()
        elif self.schedule == Schedule.QUARTERLY:
            self.initialize_quarterly_periods()
        else:
            self.initialize_custom_periods(custom_period_start_dates)

    def initialize(self, custom_period_start_dates: list = []) -> None:
        self.period_start_dates = []
        self.initialize_periods(custom_period_start_dates)
        self._dr = generate_substance(self.sub_d)
        self._al = generate_substance(self.sub_a)

        # This will initialize the "DB" but in a real world example, it would already exist
        dic = DbConn.from_initialization_string(self.db_str)
        mapping = {}
        mapping['population'] = dic
        self._db_conn = DbConn.generate_object(mapping)
        self.pool_inception = self._db_conn.get_inception_date

    @staticmethod
    def extended_start_dates(old_dates, additional_dates):
        if len(old_dates) == 0 and len(additional_dates) == 0:
            return old_dates

        year = old_dates[0].year if len(old_dates) > 0 else additional_dates[0].year
        new_date_set = set(old_dates)
        for d in additional_dates:
            if d.year != year:
                continue
            new_date_set.add(d)

        return list[sorted(new_date_set)]

    # This will add some new period boundries and reset the substance counters to empty
    #  we can then call this again to re-calculate the error to attempt to 'heal' the
    #  predictions made and get a correct answer
    def reinitialize(self, new_period_dates: list[date]):
        new_date_set = Employer.extended_start_dates(self.period_start_dates, new_period_dates)
        if len(new_date_set) <= len(self.period_start_dates):
            return False   # no new dates added

        self.period_start_dates = new_date_set
        self._dr.clear_data()
        self._al.clear_data()
        return True

    ########################################
    #  END VARIOUS INITIALIZATION METHODS  #
    ########################################

    # This is the only code that needs to pull data from the DB
    def fetch_donor_queryset_by_interval(self, start: date, end: date) -> list[int]:
        return self._db_conn.get_population_report(start, end)

    def donor_count_on(self, day: date) -> int:
        query_set = self.fetch_donor_queryset_by_interval(day, day)
        if len(query_set) > 0:
            return query_set[0]
        return 0

    def period_start_end(self, period_index: int) -> tuple:
        return (self.period_start_dates[period_index], self.period_end_date(period_index))

    # This method is the core of the calculations
    def make_period_calculations(self, period_index: int) -> None:
        # find the start and end dates of the period
        (start, end) = self.period_start_end(period_index)

        # make predictions based on:
        #  1. the poolsize on the first day of the period
        #  2. the % or the calendar year that is in this period
        #  3. the % of the population that needs to be tested
        #  4. any accumulated error from the guess we made last period
        self._al.make_apriori_predictions(self.donor_count_on(start), start, end, self.total_days_in_year)
        self._dr.make_apriori_predictions(self.donor_count_on(start), start, end, self.total_days_in_year)

        # At the end of the period, we need to get the actual average pool size of the period
        period_donor_list = self.fetch_donor_queryset_by_interval(start, end)

        # using the actual (aposteriori) data, see how far off we were and keep that
        #  for the next prediction
        self._al.determine_aposteriori_truth(period_donor_list, self.total_days_in_year)
        self._dr.determine_aposteriori_truth(period_donor_list, self.total_days_in_year)

    def run_test_scenario(self) -> int:
        self.initialize()
        for period_index in range(len(self.period_start_dates)):
            self.make_period_calculations(period_index)

        score = abs(self._dr.final_overcount()) + abs(self._al.final_overcount())
        self.make_report(2)
        return (score, self.build_report_csv())

    def rerun_test_scenario(self, new_period_dates: list[date]):
        added_dates = self.reinitialize(new_period_dates)
        if added_dates:
            for period_index in range(len(self.period_start_dates)):
                self.make_period_calculations(period_index)
            return abs(self._dr.final_overcount()) + abs(self._al.final_overcount())
        # No dates added so these numbers will not change
        print(f'WARNING: {new_period_dates} are contained in {self.period_start_dates} so no changes')
        return abs(self._dr.final_overcount()) + abs(self._al.final_overcount())

    ##############################
    #    WRITE RESULTS TO FILE   #
    ##############################

    # def write_population_to_file(self, period_start_dates) -> None:
    #     with open(f'{self.datafile}.csv', 'w') as f:
    #         period_count = 0
    #         for d in self.population:
    #             if d in period_start_dates:
    #                 f.write(f'#,Period {period_count} start\n')
    #                 period_count += 1
    #             f.write(f'{d},{self.employee_count(d)}\n')

    def make_report(self, record_level: int) -> None:
        if record_level >= 2:
            self.print_report()

        if record_level >= 3 and (self._dr.final_overcount() > 1 or self._al.final_overcount() > 1):
            self.base_print()
            print('\n*********************************************\n')
            self._al.generate_final_report()
            print('\n*********************************************\n')
            self._dr.generate_final_report()

    def average_pool_size(self, period_index: int) -> float:
        start = self.period_start_dates[period_index]
        end = self.period_end_date(period_index)
        pop = self.fetch_donor_queryset_by_interval(start, end)
        return float(sum(pop))/float(len(pop))

    def build_report_csv(self) -> str:
        initial_pop = []
        avg_pop = []
        percent_of_year = []
        for p in range(len(self.period_start_dates)):
            (start, end) = self.period_start_end(p)
            s_count = self.donor_count_on(start)
            all_donors = self.fetch_donor_queryset_by_interval(start, end)
            num_days = (end-start).days + 1
            initial_pop.append(s_count)
            avg_pop.append(float(sum(all_donors))/float(num_days))
            percent_of_year.append(float(num_days)/float(self.total_days_in_year))

        s = 'Company stats\n'
        s += f'Schedule:, {Schedule.as_str(self.schedule)}\n'
        s += f'Initial Size:, {self.start_count}\n'
        s += f'Number of periods:, {len(self.period_start_dates)}\n'
        s += ', PERIOD,START DATE,PERIOD START POOL SIZE,AVG. POOL SIZE,% of YEAR, weighted pop, error\n'
        for i, d in enumerate(self.period_start_dates):
            weighted = self.average_pool_size(i) * percent_of_year[i]
            donor_cnt = self.donor_count_on(d)
            _error = weighted * (float(self.average_pool_size(i)-self.donor_count_on(d))/max(0.0000001, float(donor_cnt)))
            s += f', period {i}, {str(d)}, {str(self.donor_count_on(d))}, {str(self.average_pool_size(i))}, {percent_of_year[i]}, {str(weighted)}, {_error}\n'
        s += f'pool as % of year:, {100.0 * self.fraction_of_year}\n'
        s += '\nApriori test predictions:\n'
        s += f'\n,drug % required:, {100.0*self.drug_percent}\n'
        s += f',initial drug guess:, {self.guess_for("drug")}\n'
        s += f'\n,alcohol % required:, {100.0*self.alcohol_percent}\n'
        s += f',initial alcohol guess:, {self.guess_for("alcohol")}\n'
        s += '\n\nDrug summary:\n'
        s += f'{self._dr.generate_period_report(initial_pop, avg_pop, percent_of_year)}'
        s += '\n\nAlcohol summary:\n'
        s += f'{self._al.generate_period_report(initial_pop, avg_pop, percent_of_year)}'
        return s

    def write_summary_report_to_file(self) -> None:
        with open(f'{self.name}_summary.csv', 'w') as f:
            f.write(self.build_report_csv())

    ##############################
    #         PRINT REPORT       #
    ##############################

    def base_print(self) -> None:
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

    def fetch_donor_query_set_for_period(self, period_index: int) -> list[int]:
        (start, end) = self.period_start_end(period_index)
        return self.fetch_donor_queryset_by_interval(start, end)

    def print_report(self):
        self.base_print()
        donor_query_set_for_period = []
        for p in range(self.num_periods):
            donor_query_set_for_period.append(self.fetch_donor_query_set_for_period(p))
        self._dr.print_report(self.total_days_in_year, donor_query_set_for_period)
        self._al.print_report(self.total_days_in_year, donor_query_set_for_period)

# TODO:
# 0. return a report in the form of a string that main can write to a text file
# 0. return a report in the form of a string that main can write to a csv file
# 1. write a "driver" that pushes data in at the start of each period to mimic how it would be used in veriport
# 2. Write "heal run" function by adding more periods and rerunning
