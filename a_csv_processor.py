
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
            if p_start < inception:
                continue
            period_start_list.append(p_start)
    else:
        for quarter in range(4):
            p_start = date(year=year, month=(quarter*3)+1, day=1)
            if p_start < inception:
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

class substance:
    def __init__(self, name, frac):
        self.name = name
        self.frac = float(frac)

        self.predicted_tests = []
        self.truth = []
        self.overcount_error = []

    @property
    def previous_cummulative_overcount_error(self) -> float:
        return sum(self.overcount_error) if len(self.overcount_error) > 0 else 0.0

    def make_prediction(self, weighted_start_count):
        from math import ceil
        apriori_estimate = weighted_start_count*self.frac
        account_for = min(apriori_estimate, self.previous_cummulative_overcount_error)
        self.predicted_tests.append(ceil(discretize_float(apriori_estimate - account_for)))

    def correct_with_true_average(self, weighted_avg_pop):
        truth = weighted_avg_pop * self.frac
        self.truth.append(truth)
        oc_error = float(self.predicted_tests[-1]) - truth
        self.overcount_error.append(oc_error)

    def print_report(self, weighted_final_average_pop):
        from math import ceil
        print(f'\n{self.name.upper()}')
        print(f'percent required: {100.0*self.frac}%')
        for i in range(len(self.predicted_tests)):
            print(f'{i+1} -> {self.predicted_tests[i]}, {self.truth[i]}, {self.overcount_error[i]}')

        print(f'num tests predicted: {sum(self.predicted_tests)}')
        print(f'num tests reqiured: {sum(self.truth)}')
        print(f'Overcount: {self.previous_cummulative_overcount_error}')

        final_float = weighted_final_average_pop*self.frac
        final_ceil = ceil(discretize_float(final_float))
        print(f'\nTrue number of tests required: {final_float}')
        print(f'True number of tests required: {final_ceil}')


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

    def print_period_stats(self):
        print('period stats:')
        for i in range(self.num_periods):
            print(f' p {i+1}: {str(self.s_date(i))} - {str(self.e_date(i))} = {self.num_days(i)}, {self.period_frac_of_year(i)}')

        print('pop stats:')
        for i in range(self.num_periods):
            print(f' p {i+1} -> start pop = {self.s_pop(i)},  avg pop = {self.avg_pop(i)} ')

        for sub in self.substances:
            print(f'{sub.name} -> {sub.frac}')



    def process_population(self):
        self.print_period_stats()
        for i in range(self.num_periods):
            weighted_start_pop = self.period_frac_of_year(i)*self.s_pop(i)
            weighted_avera_pop = self.period_frac_of_year(i)*self.avg_pop(i)
            for s in self.substances:
                s.make_prediction(weighted_start_pop)
                s.correct_with_true_average(weighted_avera_pop)

        weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
        for s in self.substances:
            s.print_report(weighted_final_average_pop)



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
    process.process_population()

if __name__ == "__main__":
    main()