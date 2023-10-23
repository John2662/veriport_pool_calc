from substance import discretize_float

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

    # def make_prediction(self, weighted_start_count):
    #     from math import ceil
    #     apriori_estimate = weighted_start_count*self.frac
    #     account_for = min(apriori_estimate, self.previous_cummulative_overcount_error)
    #     self.predicted_tests.append(ceil(discretize_float(apriori_estimate - account_for)))

    def new_make_predictions(self, period_index: int, start_count: int, period_fraction_of_year: float) -> None:
        from math import ceil
        weighted_start_pop = period_fraction_of_year * start_count
        apriori_estimate = weighted_start_pop *self.frac
        account_for = min(apriori_estimate, self.previous_cummulative_overcount_error)
        pred = ceil(discretize_float(apriori_estimate - account_for))
        if period_index < len(self.predicted_tests):
            print(f'WARNING: at period {period_index}: {pred} -> {self.predicted_tests[period_index]}')
            return None
        self.predicted_tests.append(pred)

    # def correct_with_true_average(self, weighted_avg_pop):
    #     truth = weighted_avg_pop * self.frac
    #     self.truth.append(truth)
    #     oc_error = float(self.predicted_tests[-1]) - truth
    #     self.overcount_error.append(oc_error)

    def new_correct_with_true_average(self, period_index: int, average_count: int, period_fraction_of_year: float) -> None:
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

    def process_population(self):
        print('hello form R')

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
