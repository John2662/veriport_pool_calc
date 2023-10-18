
from calendar import isleap
from datetime import date, timedelta
from dateutil.parser import parse
# from dateutil.parser import ParseError
# from dateutil.parser._parser import ParseError
import argparse

from substance import discretize_float
from file_io import load_population_from_natural_file
from file_io import load_population_from_vp_file

ROLLING_AVERAGE = True


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
    print(period_start_list)
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

class substance:
    def __init__(self, name, frac):
        self.name = name
        self.frac = float(frac)

        self.predicted_tests_rolling = []
        self.truth_rolling = []
        self.overcount_error_rolling = []
        self.reconciliation_rolling = 0.0

        self.predicted_tests_faa = []
        self.truth_faa = []
        self.overcount_error_faa = []
        self.reconciliation_faa = 0.0


    @property
    def previous_cummulative_overcount_error_rolling(self) -> float:
        return sum(self.overcount_error_rolling) if len(self.overcount_error_rolling) > 0 else 0.0

    def make_prediction_rolling(self, weighted_start_count):
        from math import ceil
        apriori_estimate = weighted_start_count*self.frac
        account_for = min(apriori_estimate, self.previous_cummulative_overcount_error_rolling)
        self.predicted_tests_rolling.append(ceil(discretize_float(apriori_estimate - account_for)))

    def correct_with_true_average_rolling(self, weighted_avg_pop):
        truth = weighted_avg_pop * self.frac
        self.truth_rolling.append(truth)
        oc_error = float(self.predicted_tests_rolling[-1]) - truth
        self.overcount_error_rolling.append(oc_error)

    def reconcile_with_current_data_rolling(self, weighted_avg_pop_recon):
        from math import ceil
        best_current_truth = weighted_avg_pop_recon * self.frac
        last_predicted = self.predicted_tests_rolling[-1]
        if best_current_truth > last_predicted:
            self.reconciliation_rolling = ceil(discretize_float(best_current_truth)) - last_predicted
            #self.reconciliation_rolling = best_current_truth - last_predicted

    @property
    def total_tests_predicted_rolling(self):
        return sum(self.predicted_tests_rolling)+self.reconciliation_rolling

    def print_report_rolling(self, weighted_final_average_pop) -> int:
        from math import ceil
        print('\n########################################')
        print(f'################# {self.name.upper()[0:4]} #################')
        print('########################################')
        print(f'percent required: {100.0*self.frac}%')
        for i in range(len(self.predicted_tests_rolling)):
            print(f'{i+1} -> {self.predicted_tests_rolling[i]}, {self.truth_rolling[i]}, {self.overcount_error_rolling[i]}')

        print(f'Overcount: {self.previous_cummulative_overcount_error_rolling}')
        print(f'num tests required: {sum(self.truth_rolling)}')
        print(f'\nnum tests predicted: {sum(self.predicted_tests_rolling)}')
        print(f'reconciliation: {self.reconciliation_rolling}')

        print(f'\nTotal tests predicted: {self.total_tests_predicted_rolling}')

        final_float = weighted_final_average_pop*self.frac
        final_ceil = ceil(discretize_float(final_float))
        print(f'\nFractional number of tests required: {final_float}')
        print(f'DOT        number tests required: {final_ceil}')

        over_count = self.total_tests_predicted_rolling - final_ceil

        if over_count > 0:
            print(f'Unfortunate Overcount: {over_count}')
        elif over_count < 0:
            print(f'\n### WARNING: Undercount: {-over_count}\n')

        return over_count


class processor:
    def __init__(self, pop: dict, monthly:bool, subst_list:list):
        self.pop = pop
        self.monthly = monthly
        self.inception = next(iter(pop))
        self.period_starts = get_period_starts(self.inception, monthly)
        self.period_ends = get_period_ends(self.period_starts)

        self.substances = []
        for s in subst_list:
            print(f'{s=}')
            for k in s:
                sub = substance(k, s[k])
                self.substances.append(sub)

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

    def recon_frac_of_year(self, s: date, e:date) -> float:
        return float((e-s).days + 1) / float(self.days_in_year)

    def print_period_stats(self):
        print('period stats:')
        for i in range(self.num_periods):
            print(f' p {i+1}: {str(self.s_date(i))} - {str(self.e_date(i))} = {self.num_days(i)}, {self.period_frac_of_year(i)}')

        print('pop stats:')
        for i in range(self.num_periods):
            print(f' p {i+1} -> start pop = {self.s_pop(i)},  avg pop = {self.avg_pop(i)} ')

        for sub in self.substances:
            print(f'{sub.name} -> {sub.frac}')

    def process_population_rolling_avg(self):
        self.print_period_stats()
        reconcile_date = date(year=self.year, month=12, day=1)
        for i in range(self.num_periods):
            weighted_start_pop = self.period_frac_of_year(i)*self.s_pop(i)
            weighted_avera_pop = self.period_frac_of_year(i)*self.avg_pop(i)
            final_period = i == self.num_periods-1 and not self.monthly

            for s in self.substances:
                s.make_prediction_rolling(weighted_start_pop)
                if final_period:
                    weighted_avg_pop_recon = self.period_frac_of_year(i) * \
                        self.recon_avg_pop(self.s_date(i), reconcile_date, self.e_date(i))
                    s.reconcile_with_current_data_rolling(weighted_avg_pop_recon)
                s.correct_with_true_average_rolling(weighted_avera_pop)

        weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
        for s in self.substances:
            count_error = s.print_report_rolling(weighted_final_average_pop)
            if count_error != 0:
                print(f'Over Error: {count_error}:')
                for p in self.pop:
                    if p <= reconcile_date:
                        continue
                    print(f'{p} -> {self.pop[p]}')

    def process_population_faa(self):
        reconcile_date = date(year=self.year, month=12, day=1)
        return 0
'''
        for i in range(self.num_periods):
            weighted_start_pop = self.period_frac_of_year(i)*self.s_pop(i)
            final_period = i == self.num_periods-1 and not self.monthly

            for s in self.substances:
                s.make_prediction_faa(weighted_start_pop)
                if final_period:
                    weighted_avg_pop_recon = self.period_frac_of_year(i) * \
                        self.recon_avg_pop(self.s_date(i), reconcile_date, self.e_date(i))
                    s.reconcile_with_current_data_faa(weighted_avg_pop_recon)

        weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
        for s in self.substances:
            count_error = s.print_report_faa(weighted_final_average_pop)
            if count_error != 0:
                print(f'Over Error: {count_error}:')
                for p in self.pop:
                    if p <= reconcile_date:
                        continue
                    print(f'{p} -> {self.pop[p]}')
'''


def main() -> int:
    args = get_args()
    print(f'{args.vp=}')
    vp = True if args.vp.lower()[0] == 't' else False
    filename = args.fp
    print(f'load {filename}')
    if vp:
        pop = load_population_from_vp_file(filename)
    else:
        pop = load_population_from_natural_file(filename)

    monthly = args.m != 'false'

    substances = [
        {'drug': .5},
        {'alcohol': .1},
    ]
    process = processor(pop, monthly, substances)
    process.process_population_rolling_avg()
    process.process_population_faa()

if __name__ == "__main__":
    main()