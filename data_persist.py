# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

import argparse
import os
import json

from schedule import Schedule
from calculator import Calculator, get_calculator_instance
from initialize_json import compile_json

from file_io import string_to_date
from file_io import write_population_to_natural_file
from file_io import write_population_to_vp_file


class VeriportDataBaseInterface:

    # self.schedule = schedule
    # self.population = population
    # self.inception = list(population.keys())[0]

    # used in calculator.py
    def store_reports(self, html: str) -> int:
        pass

    # used in calculator.py
    def persist_json(self, tmp_json, file_name) -> None:
        pass

    # used in calculator.py
    def retrieve_json(self, file_name) -> str:
        pass

    # This is the method that we need to give the output to Veriport
    def get_requirements(self, period_index: int, drug: bool) -> int:
        calc = get_calculator_instance(self.schedule, self.inception, self.population)
        return calc.get_requirements(period_index, drug)


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

    # used in main.py
    def num_periods(self) -> int:
        return len(self.period_start_dates)

    # used in calculator.py
    def store_reports(self, html: str) -> int:
        standard_schedule_str = Schedule.as_str(self.schedule)
        base_name = self.base_name + f'_{standard_schedule_str}'
        outfile = os.path.join(self.storage_dir, f'{base_name}')
        html = html.split('\n')
        with open(f'{outfile}.html', 'w') as f:
            for line in html:
                f.write(line+'\n')

    # used in calculator.py
    def persist_json(self, tmp_json, file_name) -> None:
        json_file = os.path.join(self.storage_dir, file_name)
        with open(json_file, 'w') as f:
            f.write(tmp_json)

    # used in calculator.py
    def retrieve_json(self, file_name) -> str:
        json_file = os.path.join(self.storage_dir, file_name)
        with open(json_file, 'r') as f:
            return f.read()

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
