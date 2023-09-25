# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

import argparse
import os
import json
from datetime import date, timedelta

from schedule import Schedule
from calculator import get_calculator_instance
from initialize_json import compile_json

from file_io import string_to_date
from file_io import write_population_to_natural_file
from file_io import write_population_to_vp_file


class DataPersist:

    def __init__(self,
                 schedule: Schedule,
                 population: dict,
                 base_dir: str,
                 sub_dir: str,
                 base_name: str,
                 input_data_file: str,
                 vp_format: bool):

        self.schedule = schedule
        self.population = population
        self.inception = list(population.keys())[0]
        self.base_name = base_name
        self.output_dir = os.path.join(base_dir, sub_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        # set up the storage directory to plop all the data in
        self.storage_dir = os.path.join(self.output_dir, self.base_name)
        os.makedirs(self.storage_dir, exist_ok=True)

        # make a 'generic' file name for all output (to which we can add the proper extension)
        self.output_file_basename = os.path.join(self.storage_dir, self.base_name)

        (self.employer_json_file, self.period_start_dates) = DataPersist.generate_initialization_data_files(self.population, self.schedule, self.output_file_basename)

        # needed to load the population from a file:
        self.input_data_file = input_data_file
        self.vp_format = vp_format

    # used in run_like_veriport_would
    @property
    def num_periods(self) -> int:
        return len(self.period_start_dates)

    @property
    def last_day_of_year(self) -> date:
        return self.inception.replace(month=12, day=31)

    # used in run_like_veriport_would
    def store_reports(self, html: str) -> int:
        standard_schedule_str = Schedule.as_str(self.schedule)
        base_name = self.base_name + f'_{standard_schedule_str}'
        outfile = os.path.join(self.storage_dir, f'{base_name}')
        html = html.split('\n')
        with open(f'{outfile}.html', 'w') as f:
            for line in html:
                f.write(line+'\n')

    # used in run_like_veriport_would
    def store_json(self, tmp_json, file_name) -> None:
        json_file = os.path.join(self.storage_dir, file_name)
        with open(json_file, 'w') as f:
            f.write(tmp_json)

    # used in run_like_veriport_would
    def retrieve_json(self, file_name) -> str:
        json_file = os.path.join(self.storage_dir, file_name)
        with open(json_file, 'r') as f:
            return f.read()

    # add this to better mimic the data that Veriport will load
    # the data we assume is loaded is from inception to:
    #   inception    if period_index == 0
    #   end of year  if period index >= num_periods
    #   last day of previous period otherwise
    def trim_population_to_period(self, period_index) -> dict:
        start_date = self.inception
        if period_index == 0:
            end_date = self.inception
        elif period_index >= self.num_periods:
            end_date = self.last_day_of_year
        else:
            end_date = self.period_start_dates[period_index] - timedelta(days=1)

        trimed_pop = {}
        for d in self.population:
            if d >= start_date and d <= end_date:
                trimed_pop[d] = self.population[d]
        return trimed_pop

    def run_like_veriport_would(self):
        score = 0
        dr_json = ''
        al_json = ''
        html = ''
        disallow = 0
        dr_fraction = .5
        al_fraction = .1
        debug_all_data_dr = []
        debug_all_data_al = []
        for period_index in range(self.num_periods+1):
            pop_subset = self.trim_population_to_period(period_index)
            calc = get_calculator_instance(self.schedule, self.inception, pop_subset, disallow, dr_fraction, al_fraction)

            (dr_json, al_json, score, html) = calc.process_period(period_index, dr_json, al_json)

            # persist json
            self.store_json(dr_json, 'tmp_dr.json')
            self.store_json(al_json, 'tmp_al.json')

            # flush data
            dr_json = ''
            al_json = ''

            # load data
            dr_json = self.retrieve_json('tmp_dr.json')
            al_json = self.retrieve_json('tmp_al.json')

            debug_all_data_dr = calc.get_debug_all_info(True)
            debug_all_data_al = calc.get_debug_all_info(False)

        if html is not None:
            self.store_reports(html)
            print('\ndrugs:')
            for line in debug_all_data_dr:
                print(line)
            print('alcohol:')
            for line in debug_all_data_al:
                print(line)


        return score

    # This is the method that we need to give the output to Veriport
    def get_requirements(self, period_index: int, drug: bool) -> int:
        calc = get_calculator_instance(self.schedule, self.inception, self.population)
        return calc.get_requirements(period_index, drug)

    @staticmethod
    def generate_initialization_data_files(population: dict, schedule: Schedule, generic_filepath: str) -> tuple:
        start = list(population.keys())[0]

        nat_file = generic_filepath + '_nat.csv'
        write_population_to_natural_file(population, nat_file)

        vp_file = generic_filepath + '_vp.csv'
        write_population_to_vp_file(population, vp_file)

        employer_dict = compile_json(start, schedule, disallow_zero_chance=100, dr_percent=.5, al_percent=.1)
        start_dates = []
        for d in employer_dict['period_start_dates']:
            start_dates.append(string_to_date(d))

        employer_json_file = generic_filepath + '_emp.json'

        employer_json = json.dumps(employer_dict, indent=4)
        with open(employer_json_file, 'w') as f:
            f.write(employer_json)

        return (employer_json_file, start_dates)


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Arguments: file path to write to, vp_format, mu, sigma')
    parser.add_argument('--fp', type=str, help='filepath for input file')
    parser.add_argument('--vp', type=str, help='Whether to read in VP or native format', default='false')
    args = parser.parse_args()
    return args


def main() -> int:
    from file_io import vp_to_natural
    from file_io import natural_to_vp
    args = get_args()
    print(f'{args.vp=}')
    vp = True if args.vp.lower()[0] == 't' else False
    filename = args.fp
    if vp:
        print(f'vp -> n with {filename}')
        new_filename = vp_to_natural(filename)
        print(f'n -> vp with {new_filename}')
        natural_to_vp(new_filename)
    else:
        print(f'n -> vp with {filename}')
        new_filename = natural_to_vp(filename)
        print(f'vp -> n with {new_filename}')
        vp_to_natural(new_filename)


if __name__ == "__main__":
    main()
