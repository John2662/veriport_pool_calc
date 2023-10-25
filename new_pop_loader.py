
from calendar import isleap
from datetime import date, timedelta

from new_substance_processor import SubstanceData_f, SubstanceData_r
NUM_GUESSES_TO_SET_FOR_TEST = 3

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

class Processor:
    def __init__(self, pop: dict, monthly:bool, subst_list:list):
        self.pop = pop
        self.monthly = monthly
        self.inception = next(iter(pop))
        self.period_starts = get_period_starts(self.inception, monthly)
        self.period_ends = get_period_ends(self.period_starts)

        self.substances = []
        self.substances_f = []
        self.substances_r = []
        num_periods = 12 if monthly else 4
        for s in subst_list:
            for name in s:
                fraction = s[name]
                self.substances_f.append(SubstanceData_f(name, fraction, num_periods))
                self.substances_r.append(SubstanceData_r(name, fraction, num_periods))

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
    def year(self) -> int:
        return self.inception.year

    @property
    def days_in_year(self):
        return 366 if isleap(self.inception.year) else 365

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

    # This is just an approximation for now!
    def num_total_days_in_period(self, period_index: int) -> int:
        if self.monthly:
            return 30
        return 91

    # TODO: This returns 1.0 if the inception is not in this period,
    # otherwise it gives the fractional part of the period that the pool is active
    def fraction_pool_active(self, period_index: int):
        return float((self.e_date(period_index) - self.s_date(period_index)).days) /  \
            float(self.num_total_days_in_period(period_index))

    @property
    def final_avg_pop(self) -> float:
        day_count = 0
        pop = 0
        s = self.period_starts[0]
        e = self.period_ends[-1]
        while s <= e:
            pop += self.pop[s]
            day_count += 1
            s += timedelta(days=1)
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

    def finish_period_r(self, period_index: int)-> None:
        reconcile_date = date(year=self.year, month=12, day=1)
        final_period = period_index == self.num_periods-1 and not self.monthly
        period_fraction_of_year = self.period_frac_of_year(period_index)
        for s in self.substances_r:
            if final_period and reconcile_date > self.inception:
                weighted_avg_pop_recon = self.period_frac_of_year(period_index) * \
                    self.recon_avg_pop(self.s_date(period_index), reconcile_date, self.e_date(period_index))
                s.reconcile_with_current_data(weighted_avg_pop_recon)
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
