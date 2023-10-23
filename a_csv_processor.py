
from calendar import isleap
from datetime import date, timedelta
from dateutil.parser import parse
# from dateutil.parser import ParseError
# from dateutil.parser._parser import ParseError
import argparse

from substance import discretize_float
from file_io import load_population_from_natural_file
from file_io import load_population_from_vp_file
from file_io import vp_to_natural

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
    def __init__(self, name: str, frac: float, num_periods: int):
        self.name = name
        self.frac = float(frac)
        self.num_periods = int(num_periods)

        # Rolling average data
        self.predicted_tests_rolling = []
        self.truth_rolling = []
        self.overcount_error_rolling = []
        self.reconciliation_rolling = 0.0

        # FAA calculation data
        self.predicted_tests_faa = []
        self.start_counts_faa = []
        self.fractional_periods_active_faa = []
        self.reconciliation_faa = 0.0

    def make_prediction_faa(self, start_count, fractional_period_pool_active):
        apriori_estimate = start_count*self.frac/float(self.num_periods)
        self.start_counts_faa.append(start_count)
        self.fractional_periods_active_faa.append(fractional_period_pool_active)
        self.predicted_tests_faa.append(round(discretize_float(apriori_estimate)))

    # we still need to figure out how to reconcile a quaterly with a december update
    def reconcile_with_rounded_data_faa(self, start_count: int) -> None:
        from math import ceil
        if start_count is None:
            average_size = 0.0
            for i in range(len(self.start_counts_faa)):
                average_size += float(self.start_counts_faa[i]) * self.fractional_periods_active_faa[i]
            average_size /= self.num_periods

            tests_for_calendar_year = ceil(discretize_float(average_size * self.frac))
            self.reconciliation_faa = tests_for_calendar_year - sum(self.predicted_tests_faa)

        else:
            from copy import deepcopy
            # if we get a start_count for Dec 1, then  this was quarterly, and we need to fix things up
            # we add in the "fifth" period and refigure the previously recorded numbers to
            # make it all add up

            recon_predicted_tests_faa = deepcopy(self.predicted_tests_faa)
            recon_predicted_tests_faa.append(0)

            recon_start_counts_faa = deepcopy(self.start_counts_faa)
            recon_start_counts_faa.append(start_count)

            recon_fractional_periods_active_faa = deepcopy(self.fractional_periods_active_faa)
            # remove the december from the last period (Oct 1 - Nov 30)
            recon_fractional_periods_active_faa[-1] -= 1.0/3.0
            recon_fractional_periods_active_faa.append(1.0/3.0)

            self.predicted_tests_faa = recon_predicted_tests_faa
            self.start_counts_faa = recon_start_counts_faa
            self.fractional_periods_active_faa = recon_fractional_periods_active_faa
            self.reconcile_with_rounded_data_faa(None)


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
        estimated_undercount = best_current_truth - last_predicted - sum(self.overcount_error_rolling)
        if estimated_undercount > 0:
            self.reconciliation_rolling = ceil(discretize_float(estimated_undercount))

    @property
    def total_tests_predicted_rolling(self):
        return sum(self.predicted_tests_rolling)+self.reconciliation_rolling

    @property
    def total_tests_predicted_faa(self):
        return sum(self.predicted_tests_faa)+self.reconciliation_faa

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
            print(f'\n*** WARNING: Overcount: {over_count} - roll - {self.name}\n')
        elif over_count < 0:
            print(f'\n*** ERROR:  Undercount: {-over_count} - roll - {self.name}\n')

        return over_count

    def print_report_faa(self, weighted_final_average_pop) -> int:
        from math import ceil
        print('\n########################################')
        print(f'################# {self.name.upper()[0:4]} #################')
        print('########################################')
        print(f'percent required: {100.0*self.frac}%')
        print(f'{self.predicted_tests_faa=}')
        print(f'{self.start_counts_faa=}')
        print(f'{self.fractional_periods_active_faa=}')
        for i in range(len(self.predicted_tests_faa)):
            print(f'{i+1} -> predicted: {self.predicted_tests_faa[i]}  --- start: {self.start_counts_faa[i]}')

        print(f'\nnum tests predicted: {sum(self.predicted_tests_faa)}')
        print(f'reconciliation: {self.reconciliation_faa}')

        print(f'\nTotal tests predicted: {self.total_tests_predicted_faa}')

        final_float = weighted_final_average_pop*self.frac
        final_ceil = ceil(discretize_float(final_float))
        print(f'\nFractional number of tests required: {final_float}')
        print(f'DOT        number tests required: {final_ceil}')

        over_count = self.total_tests_predicted_faa - final_ceil

        if over_count > 0:
            print(f'\n*** WARNING: Overcount: {over_count} - faa - {self.name}\n')
        elif over_count < 0:
            print(f'\n*** ERROR:  Undercount: {-over_count} - faa - {self.name}\n')

        return over_count

class processor:
    def __init__(self, pop: dict, monthly:bool, subst_list:list):
        self.pop = pop
        self.monthly = monthly
        self.inception = next(iter(pop))
        self.period_starts = get_period_starts(self.inception, monthly)
        self.period_ends = get_period_ends(self.period_starts)

        self.substances = []
        num_periods = 12 if monthly else 4
        for s in subst_list:
            print(f'{s=}')
            for k in s:
                sub = substance(k, s[k], num_periods)
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

    def process_population_rolling_avg(self):
        self.print_period_stats()
        reconcile_date = date(year=self.year, month=12, day=1)
        for i in range(self.num_periods):
            weighted_start_pop = self.period_frac_of_year(i)*self.s_pop(i)
            weighted_avera_pop = self.period_frac_of_year(i)*self.avg_pop(i)
            final_period = i == self.num_periods-1 and not self.monthly

            for s in self.substances:
                s.make_prediction_rolling(weighted_start_pop)
                if final_period and reconcile_date > self.inception:
                    weighted_avg_pop_recon = self.period_frac_of_year(i) * \
                        self.recon_avg_pop(self.s_date(i), reconcile_date, self.e_date(i))
                    s.reconcile_with_current_data_rolling(weighted_avg_pop_recon)
                s.correct_with_true_average_rolling(weighted_avera_pop)

        print('\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$ ROLLING $$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')

        weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
        for s in self.substances:
            count_error = s.print_report_rolling(weighted_final_average_pop)
            #      if count_error != 0:
            #          print(f'Over Error: {count_error}:')
            #          for p in self.pop:
            #              if p <= reconcile_date:
            #                  continue
            #              print(f'{p} -> {self.pop[p]}')

    def process_population_faa(self):
        print('hello')
        for i in range(self.num_periods):
            for s in self.substances:
                s.make_prediction_faa(self.s_pop(i), self.fraction_pool_active(i))
                # if self.monthly and i == self.num_periods-1:
                #     s.reconcile_with_rounded_data_faa(None)
                #     return None

        reconcile_date = date(year=self.year, month=12, day=1)
        if reconcile_date > self.inception:
            reconcile_pop = self.pop[reconcile_date]
            for s in self.substances:
                # if this is quaterly we need to pass in the dec 1 population
                # and figure that into the calculations
                s.reconcile_with_rounded_data_faa(reconcile_pop)

        print('\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$ FAA $$$$$$$$$$$$$$$$$$$$$$$$$')
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')

        weighted_final_average_pop = self.final_frac_of_year * self.final_avg_pop
        for s in self.substances:
            count_error = s.print_report_faa(weighted_final_average_pop)
            # if count_error != 0:
            #     print(f'Over Error: {count_error}:')
            #     for p in self.pop:
            #         if p <= reconcile_date:
            #             continue
            #         print(f'{p} -> {self.pop[p]}')


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
    process = processor(pop, monthly, substances)
    process.process_population_rolling_avg()
    process.process_population_faa()

if __name__ == "__main__":
    main()