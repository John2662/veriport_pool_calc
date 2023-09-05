# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from calculator import Calculator
from schedule import Schedule
import argparse
import os

from random_population import population_dict_from_rand
from file_io import string_to_date
from data_persist import DataPersist

MAX_NUM_TESTS = 500


class RunMan:

    def __init__(self, data_persist):
        self.data_persist = data_persist

    def get_calculator_instance(self) -> None:
        # Generate a dictionary needed to construct an instance of the Calculator class
        # Hint: The json version of this is stored in the output directory of the run
        initializing_dict = self.data_persist.get_initializing_dict()
        inception = string_to_date(initializing_dict['pool_inception'])
        schedule = Schedule.from_int_to_schedule(int(initializing_dict['schedule']))
        return Calculator(self.data_persist.population, inception, schedule)

    # Turn this into a method on Calculator
    def period_start_estimates(self, e: Calculator, period_index: int) -> None:
        (dr_tmp_json, al_tmp_json) = e.make_estimates_and_return_data_to_persist(period_index)
        self.data_persist.persist_json(dr_tmp_json, 'tmp_dr.json')
        self.data_persist.persist_json(al_tmp_json, 'tmp_al.json')

    # Turn this into a method on Calculator
    def period_end_calculations(self, calc: Calculator, period_index: int) -> None:
        tmp_dr_json = self.data_persist.retrieve_json('tmp_dr.json')
        tmp_al_json = self.data_persist.retrieve_json('tmp_al.json')
        return calc.load_persisted_data_and_do_period_calculations(period_index, tmp_dr_json, tmp_al_json)

    # Turn this into a method on Calculator
    def process_period(self, period_index: int) -> None:
        c = self.get_calculator_instance()
        if period_index == 0:
            self.period_start_estimates(c, period_index=period_index)
        if period_index == self.data_persist.final_period_index()+1:
            score = self.period_end_calculations(c, period_index=period_index-1)
            self.data_persist.store_reports(c.make_html_report())
            return score
        if period_index > 0 and period_index <= self.data_persist.final_period_index():
            self.period_end_calculations(c, period_index=period_index-1)
            self.period_start_estimates(c, period_index=period_index)
            return 0
        return 0

    def run_like_veriport_would(self):
        score = 0
        for period_index in range(self.data_persist.num_periods()+1):
            score += self.process_period(period_index)
        return score


def initialize_data_persistance(
                schedule: Schedule,
                population: dict,
                # needed to store data for the run:
                base_dir: str,
                sub_dir: str,
                base_name: str,
                # needed to load the population from a file:
                input_data_file: str,
                vp_format: bool):

    return DataPersist(
        schedule,
        population,
        base_dir,
        sub_dir,
        base_name,
        input_data_file,
        vp_format
        )


def initialize_from_args(args):
    filename = args.file

    if filename is not None:
        if not os.path.isfile(filename):
            print(f'Cannot open {filename}')
            return exit(0)
        input_data_file = filename
        sub_dir = 'fixed_trials'
        random = False
        vp_format = args.vp
    else:
        filename = ''
        input_data_file = filename
        sub_dir = 'random_trials'
        random = True
        vp_format = False

    schedule = Schedule.from_string_to_schedule(args.sch)
    base_dir = args.dir
    return (schedule, base_dir, sub_dir, input_data_file, vp_format, random)


def get_args() -> argparse.Namespace:
    # parser = argparse.ArgumentParser(description='Process some integers.')
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',
    #                     help='an integer for the accumulator')
    # parser.add_argument('--sum', dest='accumulate', action='store_const',
    #                     const=sum, default=max,
    #                     help='sum the integers (default: find the max)')
    # args = parser.parse_args()
    # print(args.accumulate(args.integers))
    parser = argparse.ArgumentParser(description='Arguments: file_to_load, vp_format, output_directory')
    parser.add_argument('--file', type=str, help='data file to load')
    parser.add_argument('--dir', type=str, help='output directory', default='test_run')
    parser.add_argument('--sch', type=str, help='the testing schedule (MONTHLY, QUARTERLY, etc.)', default='quarterly')
    parser.add_argument('--vp', type=bool, help='Whether this comes from VP or from this program', default=True)
    parser.add_argument('--iter', type=int, help='number of random iterations', default=4)
    parser.add_argument('--mu', type=float, help='mu value of gaussian', default=0.01)
    parser.add_argument('--sig', type=float, help='sigma value of gaussian', default=2.0)
    args = parser.parse_args()
    return args


def main() -> int:
    args = get_args()

    (schedule, base_dir, sub_dir, input_data_file, vp_format, random) = initialize_from_args(args)

    if not random:
        filename = args.file
        base_name = DataPersist.base_file_name_from_path(filename)
        population = DataPersist.population_dict_from_file(filename, vp_format)
        data_persist = initialize_data_persistance(schedule, population, base_dir, sub_dir, base_name, input_data_file, vp_format)
        rm = RunMan(data_persist)
        return rm.run_like_veriport_would()

    i = 0
    errors = {}
    num_tests = min(args.iter, MAX_NUM_TESTS)
    while(i < num_tests):

        base_name = f'run_{i}'
        population = population_dict_from_rand(args.mu, args.sig)
        data_persist = initialize_data_persistance(schedule, population, base_dir, sub_dir, base_name, input_data_file, vp_format)
        rm = RunMan(data_persist)
        err = rm.run_like_veriport_would()

        if err not in errors:
            errors[err] = []
        errors[err].append(i)
        i += 1

    for e in sorted(errors):
        print(f'level {e} errors: hit {len(errors[e])} errors out of {num_tests}: Runs: {errors[e]}')

    return 0


if __name__ == "__main__":
    main()
