# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, October 2023

from datetime import date
EPSILON = 0.0000000001

def discretize_float(v: float, epsilon: float = EPSILON) -> float:
    sign = -1 if v < 0 else 1
    abs_v = abs(v)
    if abs_v - int(abs_v) < epsilon:
        return sign * int(abs_v)
    return v

class SubstanceData_r:
    def __init__(self, name: str, fraction: float, min_number_tests_per_period: int = 0):
        self.name = name
        self.fraction = float(fraction)
        self.min_number_tests_per_period = min_number_tests_per_period

        self.predicted_tests = []
        self.reconciliation = {}

        # Rolling average data
        self.truth = []
        self.overcount_error = []

    def __str__(self) -> str:
        return f'{self.name}, {self.fraction}, {self.min_number_tests_per_period}\n{self.predicted_tests}\n{self.reconciliation}\n{self.truth}\n{self.overcount_error}'

    def toJson(self) -> str:
        import json
        return json.dumps(self.__dict__)

    def get_as_dict(self):
        return self.__dict__

    def get_most_recent_required_tests(self) -> int:
        if len(self.predicted_tests) == 0:
            return -1
        if len(self.reconciliation) == 0:
            return self.predicted_tests[-1]
        max_recon_date = max(self.reconciliation.keys())
        return self.reconciliation[max_recon_date]

    @property
    def previous_cummulative_overcount_error(self) -> float:
        return sum(self.overcount_error) if len(self.overcount_error) > 0 else 0.0

    def make_predictions(self, period_index: int, start_count: int, period_fraction_of_year: float) -> None:
        from math import ceil
        weighted_start_pop = period_fraction_of_year * start_count
        apriori_estimate = weighted_start_pop *self.fraction
        account_for = min(apriori_estimate, self.previous_cummulative_overcount_error)
        # don't let any prediction be < min_allowed
        pred = max(self.min_number_tests_per_period, ceil(discretize_float(apriori_estimate - account_for)))
        if period_index < len(self.predicted_tests):
            print(f'WARNING: {self.name} R: at period {period_index}: stores: {self.predicted_tests[period_index]}, ignore {pred}')
            print(f'         {self.predicted_tests=}')
            return None
        self.predicted_tests.append(pred)

    def correct_with_true_average(self, period_index: int, average_count: int, period_fraction_of_year: float) -> None:
        truth = average_count * period_fraction_of_year * self.fraction
        self.truth.append(truth)
        oc_error = float(self.predicted_tests[-1]) - truth
        self.overcount_error.append(oc_error)

    def reconcile_with_current_data(self, weighted_avg_pop_recon: float, d: date):
        from math import ceil
        best_current_truth = weighted_avg_pop_recon * self.fraction
        # THIS AND CHANGE IN Processor IMPROVES THE RECONCILIATION
        # last_predicted = self.predicted_tests[-1]
        #estimated_undercount = best_current_truth - last_predicted - sum(self.overcount_error)
        estimated_undercount = best_current_truth - sum(self.predicted_tests) - sum(self.reconciliation.values())
        if estimated_undercount > 0:
            self.reconciliation[d] = ceil(discretize_float(estimated_undercount))

    # returns False if the operation fails due to data already there
    def set_precalculated(self, precal_as_list: list[int]) -> bool:
        if len(self.predicted_tests) > 0:
            return False
        self.predicted_tests = precal_as_list
        return True


    @property
    def total_tests_predicted(self):
        return sum(self.predicted_tests)+self.reconciliation

    def print_report(self, weighted_final_average_pop) -> int:
        from math import ceil
        print('\n########################################')
        print(f'################# {self.name.upper()[0:4]} #################')
        print('########################################')
        print(f'percent required: {100.0*self.fraction}%')
        for i in range(len(self.predicted_tests)):
            print(f'{i+1} -> {self.predicted_tests[i]}, {self.truth[i]}, {self.overcount_error[i]}')

        print(f'Overcount: {self.previous_cummulative_overcount_error}')
        print(f'num tests required: {sum(self.truth)}')
        print(f'\nnum tests predicted: {sum(self.predicted_tests)}')
        print(f'reconciliation: {self.reconciliation}')

        print(f'\nTotal tests predicted: {self.total_tests_predicted}')

        final_float = weighted_final_average_pop*self.fraction
        final_ceil = ceil(discretize_float(final_float))
        print(f'\nFractional number of tests required: {final_float}')
        print(f'DOT        number tests required: {final_ceil}')

        over_count = self.total_tests_predicted - final_ceil

        if over_count > 0:
            print(f'\n*** WARNING: Overcount: {over_count} - roll - {self.name}\n')
        elif over_count < 0:
            print(f'\n*** ERROR:  Undercount: {-over_count} - roll - {self.name}\n')

        return over_count

def fromJsonDict_r(json_dict: dict) -> SubstanceData_r:
    predicted_tests = json_dict.pop("predicted_tests", [])
    reconciliation = json_dict.pop("reconciliation", {})
    truth = json_dict.pop("truth", [])
    overcount_error = json_dict.pop("overcount_error", [])
    subst = SubstanceData_r(**json_dict)
    subst.predicted_tests = predicted_tests
    subst.reconciliation = reconciliation
    subst.truth = truth
    subst.overcount_error = overcount_error
    return subst


def fromJsonStr_r(json_str: str) -> SubstanceData_r:
    import json
    json_dict = json.loads(json_str)
    return fromJsonDict_r(json_dict)


# class SubstanceData_f:
#     def __init__(self, name: str, frac: float, num_periods: int, min_tests_per_period: int = 0):
#         self.name = name
#         self.frac = float(frac)
#         self.num_periods = int(num_periods)
#         self.min_number_tests_per_period = min_tests_per_period
#
#         self.predicted_tests = []
#         self.reconciliation = 0.0
#
#         # FAA calculation data
#         self.start_counts = []
#         self.fractional_periods_active = []
#
#     def __str__(self) -> str:
#         return f'{self.name}, {self.frac}, {self.num_periods}\n{self.predicted_tests}\n{self.reconciliation}\n{self.start_counts}\n{self.fractional_periods_active}'
#
#     def toJson(self) -> str:
#         import json
#         return json.dumps(self.__dict__)
#
#     def make_predictions(self, period_index: int, start_count: int, fractional_period_pool_active: float) -> None:
#         # don't let any prediction be < min_allowed
#         min_allowed_pred = 0
#         pred = max(min_allowed_pred, start_count*self.frac/float(self.num_periods))
#         self.start_counts.append(start_count)
#         self.fractional_periods_active.append(fractional_period_pool_active)
#         if period_index < len(self.predicted_tests):
#             print(f'WARNING: {self.name} F: at period {period_index}: stores: {self.predicted_tests[period_index]}, ignore {pred}')
#             print(f'         {self.predicted_tests=}')
#             return None
#         self.predicted_tests.append(round(pred))
#
#     # we still need to figure out how to reconcile a quaterly with a december update
#     def reconcile_with_rounded_data(self, start_count: int) -> None:
#         from math import ceil
#         if start_count is None:
#             average_size = 0.0
#             for i in range(len(self.start_counts)):
#                 average_size += float(self.start_counts[i]) * self.fractional_periods_active[i]
#             average_size /= self.num_periods
#
#             tests_for_calendar_year = ceil(discretize_float(average_size * self.frac))
#             # don't let the reconcilliation be negative
#             self.reconciliation = max(0, tests_for_calendar_year - sum(self.predicted_tests))
#
#         else:
#             from copy import deepcopy
#             # if we get a start_count for Dec 1, then  this was quarterly, and we need to fix things up
#             # we add in the "fifth" period and refigure the previously recorded numbers to
#             # make it all add up
#
#             recon_predicted_tests = deepcopy(self.predicted_tests)
#             recon_predicted_tests.append(0)
#
#             recon_start_counts = deepcopy(self.start_counts)
#             recon_start_counts.append(start_count)
#
#             recon_fractional_periods_active = deepcopy(self.fractional_periods_active)
#             # remove the december from the last period (Oct 1 - Nov 30)
#             recon_fractional_periods_active[-1] -= 1.0/3.0
#             recon_fractional_periods_active.append(1.0/3.0)
#
#             self.predicted_tests = recon_predicted_tests
#             self.start_counts = recon_start_counts
#             self.fractional_periods_active = recon_fractional_periods_active
#             self.reconcile_with_rounded_data(None)
#
#     @property
#     def total_tests_predicted(self):
#         return sum(self.predicted_tests)+self.reconciliation
#
#     def print_report(self, weighted_final_average_pop) -> int:
#         from math import ceil
#         print('\n########################################')
#         print(f'################# {self.name.upper()[0:4]} #################')
#         print('########################################')
#         print(f'percent required: {100.0*self.frac}%')
#         print(f'{self.predicted_tests=}')
#         print(f'{self.start_counts=}')
#         print(f'{self.fractional_periods_active=}')
#         for i in range(len(self.predicted_tests)):
#             print(f'{i+1} -> predicted: {self.predicted_tests[i]}  --- start: {self.start_counts[i]}')
#
#         print(f'\nnum tests predicted: {sum(self.predicted_tests)}')
#         print(f'reconciliation: {self.reconciliation}')
#
#         print(f'\nTotal tests predicted: {self.total_tests_predicted}')
#
#         final_float = weighted_final_average_pop*self.frac
#         final_ceil = ceil(discretize_float(final_float))
#         print(f'\nFractional number of tests required: {final_float}')
#         print(f'DOT        number tests required: {final_ceil}')
#
#         over_count = self.total_tests_predicted - final_ceil
#
#         if over_count > 0:
#             print(f'\n*** WARNING: Overcount: {over_count} - faa - {self.name}\n')
#         elif over_count < 0:
#             print(f'\n*** ERROR:  Undercount: {-over_count} - faa - {self.name}\n')
#
#         return over_count
#
#
# def fromJson_f(json_str: str) -> SubstanceData_f:
#     import json
#     j = json.loads(json_str)
#     predicted_tests = j.pop("predicted_tests")
#     reconciliation = j.pop("reconciliation")
#     start_counts = j.pop("start_counts")
#     fractions_periods_active = j.pop("fractions_periods_active")
#     subst = SubstanceData_f(**j)
#     subst.predicted_tests = predicted_tests
#     subst.reconciliation = reconciliation
#     subst.start_counts = start_counts
#     subst.fractional_periods_active = fractions_periods_active
#     return subst
