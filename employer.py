# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
from pydantic import BaseModel
from typing import Optional
from math import ceil
import calendar

RUN_FROM_VERIPORT = True

if RUN_FROM_VERIPORT:
    from .substance import generate_substance
    from .substance import Substance
    from .schedule import Schedule
else:
    from substance import generate_substance
    from substance import Substance
    from schedule import Schedule


class Employer(BaseModel):
    schedule: Schedule

    # These get auto filled in the initialize method
    pool_inception: date
    period_start_dates: Optional[list[date]]

    # These are used to load ancillary data
    sub_d: str
    sub_a: str

    @property
    def start_count(self) -> int:
        return self.donor_count_on(self.pool_inception)

    @property
    def year(self) -> int:
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
        return float(1 + (self.last_day_of_year-self.pool_inception).days)  \
            / float(self.total_days_in_year)

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

    def initialize_periods(self, custom_period_start_dates: list[date] = []) -> None:
        self.period_start_dates = Employer.initialize_period_start_dates(
            self.pool_inception,
            self.schedule
            )

    def initialize(self, population: dict, custom_period_start_dates: list = []) -> None:
        self._population = population
        self.initialize_periods(custom_period_start_dates)

        self._dr = generate_substance(self.sub_d)
        self._al = generate_substance(self.sub_a)

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

    ########################################
    #  END VARIOUS INITIALIZATION METHODS  #
    ########################################

    def population_valid(self, start: date, end: date) -> bool:
        population = self.get_population_report(start, end)
        for d in population:
            if population[d] < 0:
                # print(f'On {str(d)} population is {population[d]} < 0')
                return False
        return True

    def get_population_report(self, start: date, end: date) -> list[int]:
        requested_population = []
        while start <= end:
            requested_population.append(self._population[start])
            start += timedelta(days=1)
        return requested_population

    @property
    def average_population(self) -> int:
        if len(self._population) == 0:
            return 0
        return round(sum(self._population.values()) / len(self._population))

    # This is the only code that needs to pull data from the DB
    def fetch_donor_queryset_by_interval(self, start: date, end: date) -> list[int]:
        return self.get_population_report(start, end)

    def donor_count_on(self, day: date) -> int:
        query_set = self.fetch_donor_queryset_by_interval(day, day)
        if len(query_set) > 0:
            return query_set[0]
        return 0

    def period_start_end(self, period_index: int) -> tuple:
        return (self.period_start_dates[period_index], self.period_end_date(period_index))

    def make_estimates(self, period_index: int) -> None:
        (start_date, end_date) = self.period_start_end(period_index)
        if period_index == 0:
            period_start_count = self.donor_count_on(start_date)
        else:
            # if we are making the calculation on the last day of the previous period,
            # we don't have the actual count for the first day of this period, so this
            # is the best we can do:
            if start_date in self._population:
                period_start_count = self.donor_count_on(start_date)
            else:
                period_start_count = self.donor_count_on(start_date-timedelta(days=1))

        self._al.make_apriori_predictions(period_start_count, start_date, end_date, self.total_days_in_year)
        self._dr.make_apriori_predictions(period_start_count, start_date, end_date, self.total_days_in_year)

    def get_data_to_persist(self) -> tuple:
        return (self._dr.data_to_persist(), self._al.data_to_persist())

    def load_persisted_data_and_do_period_calculations(
            self,
            period_index: int,
            dr_tmp_json: str,
            al_tmp_json: str
            ) -> int:
        (start_date, end_date) = self.period_start_end(period_index)
        period_donor_list = self.fetch_donor_queryset_by_interval(start_date, end_date)

        if not check_substance_json_valid(dr_tmp_json):
            print(f'ERROR: drug json {dr_tmp_json} is invalid')
        else:
            self._dr = Substance.model_validate_json(dr_tmp_json)
        if not check_substance_json_valid(al_tmp_json):
            print(f'ERROR: alcohol json {al_tmp_json} is invalid')
        else:
            self._al = Substance.model_validate_json(al_tmp_json)

        self._al.determine_aposteriori_truth(period_donor_list, self.total_days_in_year)
        self._dr.determine_aposteriori_truth(period_donor_list, self.total_days_in_year)
        return abs(self._dr.final_overcount()) + abs(self._al.final_overcount())

    ##############################
    #    GENERATE A CSV STRING   #
    ##############################

    def average_pool_size(self, period_index: int) -> float:
        start = self.period_start_dates[period_index]
        end = self.period_end_date(period_index)
        pop = self.fetch_donor_queryset_by_interval(start, end)
        return float(sum(pop))/float(len(pop))

    def generate_csv_report(self) -> str:
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
        s += f'{self._dr.generate_csv_report(initial_pop, avg_pop, percent_of_year)}'
        s += '\n\nAlcohol summary:\n'
        s += f'{self._al.generate_csv_report(initial_pop, avg_pop, percent_of_year)}'
        return s

    ##############################
    #         PRINT REPORT       #
    ##############################

    def fetch_donor_query_set_for_period(self, period_index: int) -> list[int]:
        (start, end) = self.period_start_end(period_index)
        return self.fetch_donor_queryset_by_interval(start, end)

    @staticmethod
    def format_float(f):
        return "{:6.2f}".format(float(f))

    def make_text_report(self) -> str:
        s = 'DATA KNOWN ON INCEPTION DATE:\n'
        s += f'   Num employees  : {self.start_count}\n'
        s += f'   Inception date : {self.pool_inception}\n'
        s += f'   Fractional year: {self.fraction_of_year}\n'
        s += f'\n   Wild guess at inception date for drug    : {self.guess_for("drug")}\n'
        s += f'   Wild guess at inception date for alcoho  : {self.guess_for("alcohol")}\n'
        s += '\nPOPULATION DATA AT EACH PERIOD:\n'

        donor_query_set_for_period = []

        s += '   Period |          Date Range           | % of yr |  pop  | Avg pop |  period var\n'
        for p in range(self.num_periods):
            start = self.period_start_dates[p]
            end = self.period_end_date(p)
            days = (end-start).days+1
            fract_of_year = float(days)/float(self.total_days_in_year)
            percent_of_yr = Employer.format_float(100.0*fract_of_year)

            p_data = self.fetch_donor_query_set_for_period(p)
            avg = float(sum(p_data))/float(days)
            avg_s = Employer.format_float(avg)
            w = min(p_data[0], avg) + 1
            var = Employer.format_float(float(avg-p_data[0])/w)
            s += f'        {p+1} | [{start} to {end}]={days} | {percent_of_yr}% |  {p_data[0]}  | {avg_s} | {var}\n'

            donor_query_set_for_period.append(p_data)

        s += self._dr.make_text_substance_report()
        s += self._al.make_text_substance_report()

        return s

    ##############################
    #         HTML  REPORT       #
    ##############################

    def html_period_row(self, p: int):
        start = self.period_start_dates[p]
        end = self.period_end_date(p)
        days = (end-start).days+1
        fract_of_year = float(days)/float(self.total_days_in_year)
        percent_of_yr = Employer.format_float(100.0*fract_of_year)

        p_data = self.fetch_donor_query_set_for_period(p)
        avg = float(sum(p_data))/float(days)
        # w = min(p_data[0], avg) + 1
        # var = Employer.format_float(float(avg-p_data[0])/w)
        avg_s = Employer.format_float(avg)
        s = []
        s.append('          <tr>\n')
        s.append(f'              <td>{p+1}</td>\n')
        s.append(f'              <td>{start}</td>\n')
        # s.append(f'              <td>{end}</td>\n')
        s.append(f'              <td>{days}</td>\n')
        s.append(f'              <td>{percent_of_yr}</td>\n')
        s.append(f'              <td>{p_data[0]}</td>\n')
        s.append(f'              <td>{avg_s}</td>\n')
        # s.append(f'              <td>{var}</td>\n')
        s.append('          </tr>\n')
        return s

    def make_html_report(self):
        s = ''
        s += '<!DOCTYPE html>\n'
        s += '<html lang="en">\n'
        s += '<head>\n'
        s += '  <title>Bootstrap Example</title>\n'
        s += '  <meta charset="utf-8">\n'
        s += '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        s += '  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">\n'
        s += '  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.4/jquery.min.js"></script>\n'
        s += '  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"></script>\n'
        s += '</head>\n'
        s += '<body>\n'

        s += '<div class="container">\n'
        s += '  <h2>INITIAL DATA ON INCEPTION DATE:</h2>\n'
        s += f'  <p>Initial Pool Size: {self.start_count} </p>\n'
        s += f'  <p>Inception Date: {self.pool_inception} </p>\n'
        s += f'  <p>Percent of Year: {Employer.format_float(100.0 * self.fraction_of_year)}% </p>\n'
        s += f'  <p>Initial Guess at Num Drug Tests: {self.guess_for("drug")} </p>\n'
        s += f'  <p>Initial Guess at Num Alcohol Tests: {self.guess_for("alcohol")} </p>\n'
        s += '   </br>\n'
        s += '   </hr>\n'
        s += '   </br>\n'
        s += '  <h2>POPULATION DATA PER PERIOD:</h2>\n'
        s += '  <table class="table table-striped">\n'
        s += '      <thead>\n'
        s += '          <tr>\n'
        s += '              <th>Period</th>\n'
        s += '              <th>Start Date</th>\n'
        # s += '              <th>End Date</th>\n'
        s += '              <th>Num Days</th>\n'
        s += '              <th>% of Year</th>\n'
        s += '              <th>Start Size</th>\n'
        s += '              <th>Avg. Size</th>\n'
        # s += '              <th>Variation</th>\n'
        s += '          </tr>\n'
        s += '      </thead>\n'
        s += '      <tbody>\n'

        for p in range(self.num_periods):
            row_lines = self.html_period_row(p)
            for line in row_lines:
                s += line
        s += '      </tbody>\n'
        s += '  </table>\n'
        s += '</div>\n'

        lines = self._dr.make_html_substance_report()
        for line in lines:
            s += line

        lines = self._al.make_html_substance_report()
        for line in lines:
            s += line

        s += '</body>\n'
        s += '</html>\n'
        return s

    @staticmethod
    def set_period_start_dates_by_month_list(
            pool_inception: date,
            month_list: list[int],
            bi: bool = False
            ) -> list[date]:
        period_start_dates = [pool_inception]
        year = pool_inception.year
        for m in month_list:
            d_1 = date(year=year, month=m, day=1)
            if pool_inception < d_1:
                period_start_dates.append(d_1)
            if bi:
                d_15 = date(year=year, month=m, day=15)
                if pool_inception < d_15:
                    period_start_dates.append(d_15)

        return period_start_dates

    @staticmethod
    def initialize_period_start_dates(
            pool_inception: date,
            schedule: Schedule,
            custom_period_start_dates: list[date] = []
            ) -> list[date]:
        if schedule == Schedule.SEMIMONTHLY:
            return Employer.set_period_start_dates_by_month_list(
                pool_inception, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], True)

        if schedule == Schedule.MONTHLY:
            return Employer.set_period_start_dates_by_month_list(
                pool_inception, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

        if schedule == Schedule.BIMONTHLY:
            return Employer.set_period_start_dates_by_month_list(
                pool_inception, [1, 3, 5, 7, 9, 11])

        if schedule == Schedule.QUARTERLY:
            return Employer.set_period_start_dates_by_month_list(
                pool_inception, [1, 4, 7, 10])

        if schedule == Schedule.SEMIANNUALLY:
            return Employer.set_period_start_dates_by_month_list(
                pool_inception, [1, 7])

        if schedule == Schedule.ANNUALLY:
            return Employer.set_period_start_dates_by_month_list(
                pool_inception, [1])

        period_start_dates = [pool_inception]
        for d in sorted(custom_period_start_dates):
            if d < pool_inception:
                continue
            period_start_dates.append(d)

        # dec_15 = self.pool_inception.replace(month=12, day=15)
        # if self.pool_inception < dec_15:
        #     self.period_start_dates.append(dec_15)

        return period_start_dates


def check_substance_json_valid(item):
    import json
    import pydantic
    try:
        json_item = json.loads(item)

    # Catch potential JSON formatting problems:
    except json.JSONDecodeError as exc:
        print(f'json error in parsing:\n..........\n{item}\n..........\n')
        print(f"ERROR: Invalid JSON: {exc.msg}, line \"{exc.lineno}\", column \"{exc.colno}\"")
        return False

    try:
        Substance(**json_item)

    # Catch pydantic's validation errors:
    except pydantic.ValidationError as exc:
        print(f'Schema Error:\n{json_item}\n')
        print(f"ERROR: Invalid schema: {exc}")
        return False

    return True
