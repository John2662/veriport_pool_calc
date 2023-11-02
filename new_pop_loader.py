# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, October 2023

from datetime import date, timedelta

# from .substance_processor import SubstanceData_f
from .substance_processor import SubstanceData_r, discretize_float, fromJson_r

class Processor:
    def __init__(self, pop: dict, monthly:bool, subst_list:list):
        self.pop = pop
        self.monthly = monthly
        self.inception = next(iter(pop))
        self.final_date_loaded = max(pop.keys())
        self.period_starts = Processor.get_period_starts(self.inception, monthly)
        self.period_ends = Processor.get_period_ends(self.period_starts)

        # self.substances_f = []
        self.substances_r = []
        num_periods = 12 if monthly else 4
        for s in subst_list:
            name = s['name'] if 'name' in s else 'unknown'
            fraction = float(s['fraction']) if 'fraction' in s else .5
            min_num_tests = float(s['min_tests']) if 'min_tests' in s else 0
            min_num_tests_non_neg = max(0, min_num_tests)
            # self.substances_f.append(SubstanceData_f(name, fraction, num_periods, min_num_tests_non_neg))
            self.substances_r.append(SubstanceData_r(name, fraction, min_num_tests_non_neg))

    def pprint_pop(self):
        s = ''
        for d in self.pop:
            s += f'{str(d)} -> {self.pop[d]}\n'
        return s

    def __str__(self) -> str:
        s = f'{self.pprint_pop()} \n'
        s += f'{self.monthly=}\n'
        s += f'{str(self.inception)=}\n'
        s += f'{str(self.final_date_loaded)=}\n'
        s += f'{self.period_starts=}\n'
        s += f'{self.period_ends=}\n'
        s += 'DRUGS:\n'
        s += f'{self.substances_r[0]}\n'
        s += 'ALCOHOL:\n'
        s += f'{self.substances_r[1]}\n'
        return s

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

    def get_period_index_from_start_date(self,  start_date: date) -> int:
        for period_index, d in enumerate(self.period_starts):
            if d == start_date:
                return period_index
        return -1

    # This will get just those dates that are period_start dates
    # and it will also ensure that there are none missing
    def trim_to_period_starts(self, precal: dict) -> list[int]:
        precal_as_list = []
        for d in self.period_starts:
            if d in precal:
                precal_as_list.append(precal[d])
            else:
                return precal_as_list
        return precal_as_list

    def load_substance_json_from_db(self, dr_json: dict, al_json: dict) -> None:
        self.substances_r[0] = fromJsonDict_r(dr_json)
        self.substances_r[1] = fromJsonDict_r(al_json)

    def fetch_substance_json_for_db(self) -> tuple:
        return (self.substances_r[0].toJson(), self.substances_r[1].toJson())

    # return False if this is attempting to over write values already stored
    # takes a dict precal[date] -> test
    def set_precalculated(self, substance_type: int, precal: dict)-> bool:
        precal_as_list = self.trim_to_period_starts(precal)
        return self.substances_r[substance_type].set_precalulated(precal_as_list)

    def set_precalculated_from_random_samples(self, precal: dict)-> bool:
        drug = {}
        alcohol = {}
        for s_date in precal:
            print(f"{precal[s_date][0]['dr']=}")
            drug[s_date] = precal[s_date][0]['dr']
            alcohol[s_date] = precal[s_date][0]['al']

        dr_list = self.trim_to_period_starts(drug)
        al_list = self.trim_to_period_starts(alcohol)

        return self.substances_r[0].set_precalculated(dr_list) and \
            self.substances_r[1].set_precalculated(al_list)

    # This will take the data that has been stored in the RandomSamples
    # and compare it with the in the substances.
    # There should be no difference
    def compare_precalculated_from_random_samples(self, precal: dict)-> tuple:
        drug = {}
        alcohol = {}
        for s_date in precal:
            print(f"{precal[s_date][0]['dr']=}")
            drug[s_date] = precal[s_date][0]['dr']
            alcohol[s_date] = precal[s_date][0]['al']

        dr_list = self.trim_to_period_starts(drug)
        al_list = self.trim_to_period_starts(alcohol)

        dr_error = []
        al_error = []

        for period_index, dr in enumerate(dr_list):
            if period_index >= len(self.substance_r[0].predicted_tests):
                dr_error.append(1000000*(abs(dr)+1))
            else:
                dr_error.append(dr-self.substance_r[0].predicted_tests[period_index])

        for period_index, al in enumerate(al_list):
            if period_index >= len(self.substance_r[1].predicted_tests):
                al_error.append(1000000*(abs(al)+1))
            else:
                al_error.append(al-self.substance_r[1].predicted_tests[period_index])

        return (dr_error, al_error)

    # Not really needed. Just used in testing if this approach works
    def set_guesses_r(self, guesses: dict)-> None:
        NUM_GUESSES_TO_SET_FOR_TEST = 3
        for g in guesses:
            existing_g = guesses[g][0:NUM_GUESSES_TO_SET_FOR_TEST]
            for s in self.substances_r:
                if s.name == g:
                    for val in existing_g:
                        s.predicted_tests.append(val+2)

    # def set_guesses_f(self, guesses: dict)-> None:
    #     for g in guesses:
    #         existing_g = guesses[g][0:NUM_GUESSES_TO_SET_FOR_TEST]
    #         for s in self.substances_f:
    #             if s.name == g:
    #                 for val in existing_g:
    #                     s.predicted_tests.append(val+2)

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
            print(f'{sub.name} -> {sub.fraction}')

    #   ####################################################
    #   ############ SUBSTANCE CALCULATIONS ################
    #   ####################################################

    # def process_period_f(self, period_index: int) -> None:
    #     start_date = self.period_starts[period_index]
    #     start_pop = self.pop[start_date]
    #     fractional_period_pool_active = self.fraction_pool_active(period_index)
    #     for s in self.substances_f:
    #         s.make_predictions(period_index, start_pop, fractional_period_pool_active)

    # def finish_recon_f(self):
    #     reconcile_date = date(year=self.year, month=12, day=1)
    #     if reconcile_date > self.inception:
    #         reconcile_pop = self.pop[reconcile_date]
    #         for s in self.substances_f:
    #             # if this is quaterly we need to pass in the dec 1 population
    #             # and figure that into the calculations
    #             s.reconcile_with_rounded_data(reconcile_pop)

    # def print_results_f(self):
    #     weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
    #     print('\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
    #     print('$$$$$$$$$$$$$$$ FAA $$$$$$$$$$$$$$$$$$$$$$$$$')
    #     print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
    #     for s in self.substances_f:
    #         s.print_report(weighted_final_average_pop)

    # def process_substances_f(self, print_me: bool = False) -> dict:
    #     for i in range(self.num_periods):
    #         self.process_period_f(i)
    #     self.finish_recon_f()

    #     predictions = {}
    #     for s in self.substances_f:
    #         predictions[s.name] = s.predicted_tests

    #     if print_me:
    #         self.print_results_f()
    #     return predictions

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
                    self.recon_avg_pop(self.s_date(0), d, self.e_date(period_index))
                    # THIS AND CHANGE IN Substance IMPROVES THE RECONCILIATION
                    #self.recon_avg_pop(self.s_date(period_index), d, self.e_date(period_index))
            for s in self.substances_r:
                s.reconcile_with_current_data(weighted_avg_pop_recon, d)

    def finish_period_r(self, period_index: int)-> None:
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

            final_period = i == self.num_periods-1
            if final_period:
                rds = []
                if not self.monthly:
                    rds.append(date(year=self.year, month=12, day=1))
                rds.append(date(year=self.year, month=12, day=15))
                rds.append(date(year=self.year, month=12, day=22))
                rds.append(date(year=self.year, month=12, day=29))
                self.perform_reconciliation(i, rds)

            self.finish_period_r(i)

        predictions = {}
        for s in self.substances_r:
            predictions[s.name] = s.predicted_tests

        if print_me:
            self.print_results_r()
        return predictions

    def process_current_period(self, period_index: int, reconciliation_date: date = None) -> tuple:
        if period_index > 0 and period_index < self.num_periods:
            self.finish_period_r(period_index-1)

        if period_index < self.num_periods:
            # make estimates for the next period
            self.process_period_r(period_index)
        elif reconciliation_date is not None:
            self.perform_reconciliation([reconciliation_date])
        else:
            self.finish_period_r(period_index-1)

        return (self.substances_r[0].get_as_dict(), self.substance_r[1].get_as_dict())

    def get_most_recent_required_tests(self, subst: int) -> int:
        if subst == 0:
            return self.substances_r[0].get_most_recent_required_tests()
        return self.substances_r[1].get_most_recent_required_tests()


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
        results['drug_tests'] = ceil(discretize_float(avg_pop * self.substances_r[0].fraction))
        results['alcohol_tests'] = ceil(discretize_float(avg_pop * self.substances_r[1].fraction))
        return results

    def r_estimate(self):
        results = {}
        results['inception'] = str(self.inception)
        results['through'] = str(self.final_date_loaded)
        dr_reconciliation = sum(self.substances_r[0].reconciliation.values())
        al_reconciliation = sum(self.substances_r[1].reconciliation.values())
        results['drug_tests'] = int(sum(self.substances_r[0].predicted_tests)+dr_reconciliation)
        results['alcohol_tests'] = int(sum(self.substances_r[1].predicted_tests)+al_reconciliation)
        return results

    # def f_estimate(self):
    #     results = {}
    #     results['inception'] = str(self.inception)
    #     results['through'] = str(self.final_date_loaded)
    #     results['drug_tests'] = sum(self.substances_f[0].predicted_tests)+self.substances_f[0].reconciliation
    #     results['alcohol_tests'] = sum(self.substances_f[1].predicted_tests)+self.substances_f[1].reconciliation
    #     return results

    def process_loaded_data(self):
        self.process_substances_r(False)
        # self.process_substances_f(False)

    def generate_csv_report(self) -> list[str]:
        # print period by period what the substances are generating
        array = [f'monthly: {self.monthly}']
        array.append(f'inception: {str(self.inception)}')
        array.append(f'final date: {str(self.final_date_loaded)}')
        dr_frac = self.substances_r[0].fraction
        al_frac = self.substances_r[1].fraction

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
                if period_index >= len(subst.predicted_tests):
                    continue
                s = f',,,{subst.name},{subst.predicted_tests[period_index]},'
                s += f'{subst.truth[period_index]},'
                s += f'{subst.overcount_error[period_index]},'
                recon = sum(subst.reconciliation.values())
                s += f'{sum(subst.predicted_tests[0:period_index+1])+recon},'
                array.append(s)
            array.append('')

        return array

