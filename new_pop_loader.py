# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, October 2023

from datetime import date, timedelta

from .substance_processor import SubstanceData_f, SubstanceData_r, discretize_float
NUM_GUESSES_TO_SET_FOR_TEST = 3

class Processor:
    def __init__(self, pop: dict, monthly:bool, subst_list:list):
        self.pop = pop
        self.monthly = monthly
        self.inception = next(iter(pop))
        self.final_date_loaded = max(pop.keys())
        self.period_starts = Processor.get_period_starts(self.inception, monthly)
        self.period_ends = Processor.get_period_ends(self.period_starts)

        # self.substances = []
        self.substances_f = []
        self.substances_r = []
        num_periods = 12 if monthly else 4
        for s in subst_list:
            for name in s:
                fraction = s[name]
                self.substances_f.append(SubstanceData_f(name, fraction, num_periods))
                self.substances_r.append(SubstanceData_r(name, fraction, num_periods))

    @staticmethod
    def get_period_starts(inception: date, monthly: bool) -> list[date]:
        year = inception.year
        period_start_list = [inception]
        if monthly:
            for month in range(12):
                p_start = date(year=year, month=month+1, day=1)
                if p_start <= inception:
                    continue
                period_start_list.append(p_start)
        else:
            for quarter in range(4):
                p_start = date(year=year, month=(quarter*3)+1, day=1)
                if p_start <= inception:
                    continue
                period_start_list.append(p_start)
        return period_start_list

    @staticmethod
    def get_period_ends(period_starts: list[date]) -> list[date]:
        year = period_starts[0].year
        period_ends = []
        for i, p in enumerate(period_starts):
            if i == 0:
                continue
            end= p-timedelta(days=1)
            period_ends.append(end)
        period_ends.append(date(year=year,month=12,day=31))
        return period_ends

    @property
    def num_fully_loaded_periods(self) -> int:
        for period_index in reversed(range(len(self.period_ends))):
            if self.period_ends[period_index] <= self.final_date_loaded:
                return period_index + 1

            if self.period_starts[period_index] <= self.final_date_loaded:
                return period_index
        return 0

    def set_guesses_r(self, guesses: dict)-> None:
        for g in guesses:
            existing_g = guesses[g][0:NUM_GUESSES_TO_SET_FOR_TEST]
            for s in self.substances_r:
                if s.name == g:
                    for val in existing_g:
                        s.predicted_tests.append(val+2)

    def set_guesses_f(self, guesses: dict)-> None:
        for g in guesses:
            existing_g = guesses[g][0:NUM_GUESSES_TO_SET_FOR_TEST]
            for s in self.substances_f:
                if s.name == g:
                    for val in existing_g:
                        s.predicted_tests.append(val+2)

    @property
    def dec_31(self) -> date:
        return date(year=self.inception.year, month=12, day=31)

    @property
    def year(self) -> int:
        return self.inception.year

    @property
    def is_leap_count(self) -> int:
        from calendar import isleap
        if isleap(self.inception.year):
            return 1
        return 0

    @property
    def days_in_year(self):
        return 365 + self.is_leap_count

    @property
    def num_periods(self) -> int:
        return len(self.period_starts)

    def s_date(self, period_index:int) -> date:
        return self.period_starts[period_index]

    def e_date(self, period_index:int) -> date:
        return self.period_ends[period_index]

    def s_pop(self, period_index:int) -> int:
        return self.pop[self.s_date(period_index)]

    def num_days(self, period_index: int) -> int:
        return (self.e_date(period_index)-self.s_date(period_index)).days+1

    def num_total_days_in_period(self, period_index: int) -> int:
        feb = 28+self.is_leap_count
        day_count = [31, feb, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 ]
        if self.monthly:
            return day_count[period_index]
        return sum(day_count[3*period_index: 3*(period_index+1)])

    # TODO: This returns 1.0 if the inception is not in this period,
    # otherwise it gives the fractional part of the period that the pool is active
    def fraction_pool_active(self, period_index: int):
        return float((self.e_date(period_index) - self.s_date(period_index)).days) /  \
            float(self.num_total_days_in_period(period_index))

    def final_avg_pop(self, full_year: bool = False) -> float:
        day_count = 0
        pop = 0
        s = self.period_starts[0]
        e = self.period_ends[-1]
        while s <= e:
            pop += self.pop[s]
            day_count += 1
            s += timedelta(days=1)
        if full_year:
            return float(pop)/float(self.days_in_year)

        return float(pop)/float(day_count)

    @property
    def final_frac_of_year(self) -> float:
        return float((self.period_ends[-1] - self.inception).days + 1) / float(self.days_in_year)

    def avg_pop(self, period_index:int) -> int:
        s = self.s_date(period_index)
        e = self.e_date(period_index)
        day_count = 0
        pop = 0
        while s <= e:
            pop += self.pop[s]
            day_count += 1
            s += timedelta(days=1)
        return float(pop)/float(day_count)

    def period_frac_of_year(self, period_index: int) -> float:
        return float(self.num_days(period_index)) / float(self.days_in_year)

    def recon_avg_pop(self, s: date, r:date, e:date) -> float:
        day_count = 0
        pop = 0
        while s <= e:
            pop += self.pop[min(s, r)]
            day_count += 1
            s += timedelta(days=1)
        return float(pop)/float(day_count)

    def print_period_stats(self):
        print('period stats:')
        for i in range(self.num_periods):
            print(f' p {i+1}: {str(self.s_date(i))} - {str(self.e_date(i))} = {self.num_days(i)}, {self.period_frac_of_year(i)}')

        print('pop stats:')
        for i in range(self.num_periods):
            print(f' p {i+1} -> start pop = {self.s_pop(i)},  avg pop = {self.avg_pop(i)} ')

        for sub in self.substances:
            print(f'{sub.name} -> {sub.frac}')

    #   ####################################################
    #   ############ SUBSTANCE CALCULATIONS ################
    #   ####################################################

    def process_period_f(self, period_index: int) -> None:
        start_date = self.period_starts[period_index]
        start_pop = self.pop[start_date]
        fractional_period_pool_active = self.fraction_pool_active(period_index)
        for s in self.substances_f:
            s.make_predictions(period_index, start_pop, fractional_period_pool_active)

    def finish_recon_f(self):
        reconcile_date = date(year=self.year, month=12, day=1)
        if reconcile_date > self.inception:
            reconcile_pop = self.pop[reconcile_date]
            for s in self.substances_f:
                # if this is quaterly we need to pass in the dec 1 population
                # and figure that into the calculations
                s.reconcile_with_rounded_data(reconcile_pop)

    def print_results_f(self):
        weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
        print('\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$ FAA $$$$$$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        for s in self.substances_f:
            s.print_report(weighted_final_average_pop)

    def process_substances_f(self, print_me: bool = False) -> dict:
        for i in range(self.num_periods):
            self.process_period_f(i)
        self.finish_recon_f()

        predictions = {}
        for s in self.substances_f:
            predictions[s.name] = s.predicted_tests

        if print_me:
            self.print_results_f()
        return predictions

    def process_period_r(self, period_index: int) -> None:
        start_date = self.period_starts[period_index]
        start_pop = self.pop[start_date]
        period_fraction_of_year = self.period_frac_of_year(period_index)
        for s in self.substances_r:
            s.make_predictions(period_index, start_pop, period_fraction_of_year)

    def perform_reconciliation(self, period_index: int, dates: list[date]) -> None:
        for d in dates:
            if d <= self.inception:
                continue
            weighted_avg_pop_recon = self.period_frac_of_year(period_index) * \
                    self.recon_avg_pop(self.s_date(period_index), d, self.e_date(period_index))
            for s in self.substances_r:
                s.reconcile_with_current_data(weighted_avg_pop_recon, d)


    def finish_period_r(self, period_index: int)-> None:
        rd_1 = date(year=self.year, month=12, day=1)
        rd_2 = date(year=self.year, month=12, day=15)
        rd_3 = date(year=self.year, month=12, day=22)
        rd_4 = date(year=self.year, month=12, day=29)
        final_period = period_index == self.num_periods-1 and not self.monthly
        if final_period:
            self.perform_reconciliation(period_index, [rd_1, rd_2, rd_3, rd_4])

        period_fraction_of_year = self.period_frac_of_year(period_index)
        for s in self.substances_r:
            average_pop = self.avg_pop(period_index)
            s.correct_with_true_average(period_index, average_pop, period_fraction_of_year)

    def print_results_r(self):
        weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
        print('\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$ ROLLING $$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        for s in self.substances_r:
            s.print_report(weighted_final_average_pop)

    def process_substances_r(self, print_me: bool = False) -> dict:
        for i in range(self.num_periods):
            self.process_period_r(i)
            self.finish_period_r(i)

        predictions = {}
        for s in self.substances_r:
            predictions[s.name] = s.predicted_tests

        if print_me:
            self.print_results_r()
        return predictions

    def current_DOT_estimate(self) -> dict:
        from math import ceil
        results = {}
        results['inception'] = str(self.inception)
        results['through'] = str(self.final_date_loaded)
        avg_pop = 0
        s = self.inception
        last_valid_pop = 0
        while s <= self.dec_31:
            if s in self.pop.keys():
                last_valid_pop = self.pop[s]
            avg_pop += last_valid_pop
            s += timedelta(days=1)
        avg_pop = float(avg_pop) / float(self.days_in_year)
        results['drug_tests'] = ceil(discretize_float(avg_pop * self.substances_r[0].frac))
        results['alcohol_tests'] = ceil(discretize_float(avg_pop * self.substances_r[1].frac))
        return results

    def r_estimate(self):
        results = {}
        results['inception'] = str(self.inception)
        results['through'] = str(self.final_date_loaded)
        dr_reconciliation = sum(self.substances_r[0].reconciliation.values())
        al_reconciliation = sum(self.substances_r[1].reconciliation.values())
        results['drug_tests'] = sum(self.substances_r[0].predicted_tests)+float(dr_reconciliation)
        results['alcohol_tests'] = sum(self.substances_r[1].predicted_tests)+float(al_reconciliation)
        return results

    def f_estimate(self):
        results = {}
        results['inception'] = str(self.inception)
        results['through'] = str(self.final_date_loaded)
        results['drug_tests'] = sum(self.substances_f[0].predicted_tests)+self.substances_f[0].reconciliation
        results['alcohol_tests'] = sum(self.substances_f[1].predicted_tests)+self.substances_f[1].reconciliation
        return results

    def process_loaded_data(self):
        self.process_substances_r(False)
        self.process_substances_f(False)

    def generate_csv_report(self) -> list[str]:
        # print period by period what the substances are generating
        array = [f'monthly: {self.monthly}']
        array.append(f'inception: {str(self.inception)}')
        array.append(f'final date: {str(self.final_date_loaded)}')
        dr_frac = self.substances_r[0].frac
        al_frac = self.substances_r[1].frac

        array.append(f'substance: {self.substances_r[0].name}, fraction:, {dr_frac}')
        array.append(f'substance: {self.substances_r[1].name}, fraction:, {al_frac}')
        avg_pop = self.final_avg_pop(full_year=True)
        array.append(f'average pool size:, {avg_pop}')
        array.append(f'minimal drug tests:, {avg_pop*dr_frac}')
        array.append(f'minimal alco tests:, {avg_pop*al_frac}')

        array.append(f'')
        array.append(f'Size data:')
        array.append(f'')



        for period_index in range(len(self.period_starts)):
            s = self.period_starts[period_index]
            e = self.period_ends[period_index]
            array.append(f',,,period: {period_index}, from: {str(s)}, to: {e}')
            for d in self.pop:
                # while d < s:
                #     continue
                # if d > e:
                #     break
                if d >= s and d <= e:
                    array.append(f'{d},{self.pop[d]}')

            array.append('')
            array.append(f',,,substance,predicted,truth,overcount,cummulative predicted')
            for subst in self.substances_r:
                s = f',,,{subst.name},{subst.predicted_tests[period_index]},'
                s += f'{subst.truth[period_index]},'
                s += f'{subst.overcount_error[period_index]},'
                recon = sum(subst.reconciliation.values())
                s += f'{sum(subst.predicted_tests[0:period_index+1])+recon},'
                array.append(s)
            array.append('')

        return array

