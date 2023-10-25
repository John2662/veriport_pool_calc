EPSILON = 0.0000000001

def discretize_float(v: float, epsilon: float = EPSILON) -> float:
    sign = -1 if v < 0 else 1
    abs_v = abs(v)
    if abs_v - int(abs_v) < epsilon:
        return sign * int(abs_v)
    return v

class SubstanceData_r:
    def __init__(self, name: str, frac: float, num_periods: int):
        self.name = name
        self.frac = float(frac)
        self.num_periods = int(num_periods)

        self.predicted_tests = []
        self.reconciliation = 0.0

        # Rolling average data
        self.truth = []
        self.overcount_error = []

    @property
    def previous_cummulative_overcount_error(self) -> float:
        return sum(self.overcount_error) if len(self.overcount_error) > 0 else 0.0

    def make_predictions(self, period_index: int, start_count: int, period_fraction_of_year: float) -> None:
        from math import ceil
        weighted_start_pop = period_fraction_of_year * start_count
        apriori_estimate = weighted_start_pop *self.frac
        account_for = min(apriori_estimate, self.previous_cummulative_overcount_error)
        # don't let any prediction be < min_allowed
        min_allowed_pred = 0
        pred = max(min_allowed_pred, ceil(discretize_float(apriori_estimate - account_for)))
        if period_index < len(self.predicted_tests):
            print(f'WARNING: {self.name} R: at period {period_index}: stores: {self.predicted_tests[period_index]}, ignore {pred}')
            print(f'         {self.predicted_tests=}')
            return None
        self.predicted_tests.append(pred)

    def correct_with_true_average(self, period_index: int, average_count: int, period_fraction_of_year: float) -> None:
        truth = average_count * period_fraction_of_year * self.frac
        self.truth.append(truth)
        oc_error = float(self.predicted_tests[-1]) - truth
        self.overcount_error.append(oc_error)


    def reconcile_with_current_data(self, weighted_avg_pop_recon):
        from math import ceil
        best_current_truth = weighted_avg_pop_recon * self.frac
        last_predicted = self.predicted_tests[-1]
        estimated_undercount = best_current_truth - last_predicted - sum(self.overcount_error)
        if estimated_undercount > 0:
            self.reconciliation = ceil(discretize_float(estimated_undercount))

    @property
    def total_tests_predicted(self):
        return sum(self.predicted_tests)+self.reconciliation

    def print_report(self, weighted_final_average_pop) -> int:
        from math import ceil
        print('\n########################################')
        print(f'################# {self.name.upper()[0:4]} #################')
        print('########################################')
        print(f'percent required: {100.0*self.frac}%')
        for i in range(len(self.predicted_tests)):
            print(f'{i+1} -> {self.predicted_tests[i]}, {self.truth[i]}, {self.overcount_error[i]}')

        print(f'Overcount: {self.previous_cummulative_overcount_error}')
        print(f'num tests required: {sum(self.truth)}')
        print(f'\nnum tests predicted: {sum(self.predicted_tests)}')
        print(f'reconciliation: {self.reconciliation}')

        print(f'\nTotal tests predicted: {self.total_tests_predicted}')

        final_float = weighted_final_average_pop*self.frac
        final_ceil = ceil(discretize_float(final_float))
        print(f'\nFractional number of tests required: {final_float}')
        print(f'DOT        number tests required: {final_ceil}')

        over_count = self.total_tests_predicted - final_ceil

        if over_count > 0:
            print(f'\n*** WARNING: Overcount: {over_count} - roll - {self.name}\n')
        elif over_count < 0:
            print(f'\n*** ERROR:  Undercount: {-over_count} - roll - {self.name}\n')

        return over_count

class SubstanceData_f:
    def __init__(self, name: str, frac: float, num_periods: int):
        self.name = name
        self.frac = float(frac)
        self.num_periods = int(num_periods)

        self.predicted_tests = []
        self.reconciliation = 0.0

        # FAA calculation data
        self.start_counts = []
        self.fractional_periods_active = []

    def make_predictions(self, period_index: int, start_count: int, fractional_period_pool_active: float) -> None:
        # don't let any prediction be < min_allowed
        min_allowed_pred = 0
        pred = max(min_allowed_pred, start_count*self.frac/float(self.num_periods))
        self.start_counts.append(start_count)
        self.fractional_periods_active.append(fractional_period_pool_active)
        if period_index < len(self.predicted_tests):
            print(f'WARNING: {self.name} F: at period {period_index}: stores: {self.predicted_tests[period_index]}, ignore {pred}')
            print(f'         {self.predicted_tests=}')
            return None
        self.predicted_tests.append(round(pred))

    # we still need to figure out how to reconcile a quaterly with a december update
    def reconcile_with_rounded_data(self, start_count: int) -> None:
        from math import ceil
        if start_count is None:
            average_size = 0.0
            for i in range(len(self.start_counts)):
                average_size += float(self.start_counts[i]) * self.fractional_periods_active[i]
            average_size /= self.num_periods

            tests_for_calendar_year = ceil(discretize_float(average_size * self.frac))
            # don't let the reconcilliation be negative
            self.reconciliation = max(0, tests_for_calendar_year - sum(self.predicted_tests))

        else:
            from copy import deepcopy
            # if we get a start_count for Dec 1, then  this was quarterly, and we need to fix things up
            # we add in the "fifth" period and refigure the previously recorded numbers to
            # make it all add up

            recon_predicted_tests = deepcopy(self.predicted_tests)
            recon_predicted_tests.append(0)

            recon_start_counts = deepcopy(self.start_counts)
            recon_start_counts.append(start_count)

            recon_fractional_periods_active = deepcopy(self.fractional_periods_active)
            # remove the december from the last period (Oct 1 - Nov 30)
            recon_fractional_periods_active[-1] -= 1.0/3.0
            recon_fractional_periods_active.append(1.0/3.0)

            self.predicted_tests = recon_predicted_tests
            self.start_counts = recon_start_counts
            self.fractional_periods_active = recon_fractional_periods_active
            self.reconcile_with_rounded_data(None)

    @property
    def total_tests_predicted(self):
        return sum(self.predicted_tests)+self.reconciliation

    def print_report(self, weighted_final_average_pop) -> int:
        from math import ceil
        print('\n########################################')
        print(f'################# {self.name.upper()[0:4]} #################')
        print('########################################')
        print(f'percent required: {100.0*self.frac}%')
        print(f'{self.predicted_tests=}')
        print(f'{self.start_counts=}')
        print(f'{self.fractional_periods_active=}')
        for i in range(len(self.predicted_tests)):
            print(f'{i+1} -> predicted: {self.predicted_tests[i]}  --- start: {self.start_counts[i]}')

        print(f'\nnum tests predicted: {sum(self.predicted_tests)}')
        print(f'reconciliation: {self.reconciliation}')

        print(f'\nTotal tests predicted: {self.total_tests_predicted}')

        final_float = weighted_final_average_pop*self.frac
        final_ceil = ceil(discretize_float(final_float))
        print(f'\nFractional number of tests required: {final_float}')
        print(f'DOT        number tests required: {final_ceil}')

        over_count = self.total_tests_predicted - final_ceil

        if over_count > 0:
            print(f'\n*** WARNING: Overcount: {over_count} - faa - {self.name}\n')
        elif over_count < 0:
            print(f'\n*** ERROR:  Undercount: {-over_count} - faa - {self.name}\n')

        return over_count
