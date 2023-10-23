
from calendar import isleap
from datetime import date, timedelta
from dateutil.parser import parse
# from dateutil.parser import ParseError
# from dateutil.parser._parser import ParseError
import argparse

from file_io import load_population_from_natural_file
from file_io import load_population_from_vp_file
from file_io import vp_to_natural

from substance_processor import SubstanceData_f, SubstanceData_r

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Arguments: file path to write to, vp_format'
        )
    parser.add_argument(
        '--fp',
        type=str,
        help='filepath for input file'
        )
    parser.add_argument(
        '--vp',
        type=str,
        help='Whether to read in VP or native format',
        default='true'
        )
    parser.add_argument(
        '--m',
        type=str,
        help='Whether to process monthly (quarterly is default)',
        default='false'
        )
    args = parser.parse_args()
    return args

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

    def set_guesses(self, guesses: dict, faa: bool)-> None:
        num_to_do = 3
        if faa:
            for g in guesses:
                existing_g = guesses[g][0:num_to_do]
                print(f'{existing_g=}')
                for s in self.substances_f:
                    if s.name == g:
                        for val in existing_g:
                            s.predicted_tests.append(val+2)
                for s in self.substances_f:
                    print(f'  FAA: {s.name} -> {s.predicted_tests=}')

        else:
            for g in guesses:
                existing_g = guesses[g][0:num_to_do]
                print(f'{existing_g=}')
                for s in self.substances_r:
                    if s.name == g:
                        for val in existing_g:
                            s.predicted_tests.append(val+2)
                for s in self.substances_r:
                    print(f' ROLL: {s.name} -> {s.predicted_tests=}')

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

def main() -> int:
    args = get_args()
    print(f'{args.vp=}')
    vp = True if args.vp.lower()[0] == 't' else False
    filename = args.fp
    print(f'load {filename}')
    if vp:
        pop = load_population_from_vp_file(filename)
        nat_file = filename[:-4]
        nat_file += '_nat.csv'
        #print(f'{nat_file=}')
        #vp_to_natural(filename, nat_file)
    else:
        pop = load_population_from_natural_file(filename)

    monthly = args.m != 'false'

    substances = [
        {'drug': .25},
        {'alcohol': .1},
    ]
    process = Processor(pop, monthly, substances)
    r_predictions = process.process_substances_r(True)
    f_predictions = process.process_substances_f(True)

    for name in r_predictions:
        print(f'{name[0:4]} -> {r_predictions[name]=}')
    for name in r_predictions:
        print(f'{name[0:4]} -> {f_predictions[name]=}')

    process2 = Processor(pop, monthly, substances)
    process2.set_guesses(r_predictions, False)
    process2.set_guesses(f_predictions, True)

    #print('ROLL')
    #for s in process2.substances_r:
    #    print(f'->{s.predicted_tests=}')
    #print('FAA')
    #for s in process2.substances_f:
    #    print(f'->{s.predicted_tests=}')

    r_predictions_2 = process2.process_substances_r(True)
    f_predictions_2 = process2.process_substances_f(True)

    print('ROLL')
    for name in r_predictions_2:
        print(f'old: {name[0:4]} -> {r_predictions[name]} = {sum(r_predictions[name])}')
        print(f'new: {name[0:4]} -> {r_predictions_2[name]} = {sum(r_predictions_2[name])}')
    print('FAA')
    for name in f_predictions_2:
        print(f'old: {name[0:4]} -> {f_predictions[name]} = {sum(f_predictions[name])}')
        print(f'new: {name[0:4]} -> {f_predictions_2[name]} = {sum(f_predictions_2[name])}')

if __name__ == "__main__":
    main()
