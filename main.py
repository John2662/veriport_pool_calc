# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Schedule, Employer
from initialize_json import compile_json
from datetime import date
import argparse
import os
import json

from random_population import generate_random_population_data
from file_io import load_population_from_natural_file
from file_io import load_population_from_vp_file
from file_io import write_population_to_vp_file
from file_io import write_population_to_natural_file
from file_io import string_to_date

# This is valid for the length of the run, then removed in main()
MAX_NUM_TESTS = 500


def tokenize_string(s: str, t: str = '\n') -> list[str]:
    return s.split(t)


def store_data(pop: dict, html: str, directory: os.path = 'run_output', file_name: str = '') -> None:
    outfile = os.path.join(directory, f'{file_name}')
    html = tokenize_string(html)
    with open(f'{outfile}.html', 'w') as f:
        for line in html:
            f.write(line+'\n')


def population_dict_from_file(datafile: str, vp_format: bool) -> dict:
    if vp_format:
        return load_population_from_vp_file(datafile)
    else:
        return load_population_from_natural_file(datafile)


def population_dict_from_rand(mu: float, sigma: float) -> dict:
    return generate_random_population_data(mu, sigma)


def from_string_to_schedule(s):
    s = s.strip().lower()
    if s == 'semimonthly':
        return Schedule.SEMIMONTHLY
    if s == 'monthly':
        return Schedule.MONTHLY
    if s == 'bimonthly':
        return Schedule.BIMONTHLY
    if s == 'quarterly':
        return Schedule.QUARTERLY
    if s == 'semiannually':
        return Schedule.SEMIANNUALLY
    if s == 'annually':
        return Schedule.ANNUALLY
    print('hit default: QUARTERLY')
    return Schedule.QUARTERLY


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
    parser.add_argument('--mu', type=float, help='mu value of gaussian', default=0.0)
    parser.add_argument('--sig', type=float, help='sigma value of gaussian', default=0.0)
    args = parser.parse_args()
    return args


def base_file_name_from_path(filepath: str) -> str:
    split_filepath = filepath.split('/')
    just_file_name = os.path.splitext(split_filepath[-1])[0]
    return just_file_name


def generate_initialization_data_files(population: dict, schedule: Schedule, write_file: str) -> tuple:
    start = list(population.keys())[0]

    nat_file = write_file + '_nat.csv'
    write_population_to_natural_file(population, nat_file)

    vp_file = write_file + '_vp.csv'
    write_population_to_vp_file(population, vp_file)

    employer_dict = compile_json(start, schedule, vp_file)
    start_dates = []
    for d in employer_dict['period_start_dates']:
        start_dates.append(string_to_date(d))

    employer_json_file = write_file + '_emp.json'
    write_employer_initialization_dict_to_file(employer_json_file, employer_dict)

    return (employer_json_file, start_dates)


def write_employer_initialization_dict_to_file(employer_json_file: str, employer_dict: dict) -> None:
    employer_json = json.dumps(employer_dict, indent=4)
    with open(employer_json_file, 'w') as f:
        f.write(employer_json)


def load_employer_initialization_dict_from_file(filename: str) -> dict:
    with open(filename, 'r') as f:
        employer_dict = json.load(f)
        return employer_dict


def construct_employer(employer_json: str) -> Employer:
    return Employer(**employer_json)


class run_man:
    base_dir: str
    sub_dir: str
    input_data_file: str
    run_number: str
    mu: float
    sigma: float

    def __init__(self, schedule: Schedule, base_dir: str, sub_dir: str, input_data_file: str, vp_format: bool = True, run_number: int = -1, mu: float = 0.0, sigma: float = 0.0) -> None:
        self.schedule = schedule

        output_dir = os.path.join(base_dir, sub_dir)
        os.makedirs(output_dir, exist_ok=True)

        if run_number < 0:
            self.population = population_dict_from_file(input_data_file, vp_format)
            self.base_name = base_file_name_from_path(input_data_file)
        else:
            self.population = population_dict_from_rand(mu, sigma)
            self.base_name = f'run_{run_number}'

        self.storage_dir = os.path.join(output_dir, self.base_name)
        os.makedirs(self.storage_dir, exist_ok=True)

        output_file_basename = os.path.join(self.storage_dir, self.base_name)
        (self.employer_json_file, self.period_start_dates) = generate_initialization_data_files(self.population, self.schedule, output_file_basename)

    def get_period_start_dates(self) -> list[date]:
        return self.period_start_dates

    def get_initializing_dict(self) -> dict:
        return load_employer_initialization_dict_from_file(self.employer_json_file)

    def run_test_case(self) -> int:
        employer_dict = load_employer_initialization_dict_from_file(self.employer_json_file)
        employer = construct_employer(employer_dict)
        (err, html) = employer.run_test_scenario()
        return self.store_reports(err, html)

    def store_reports(self, html: str) -> int:
        # Add the periodicity to the file name
        standard_schedule_str = Schedule.as_str(self.schedule)
        base_name = self.base_name + f'_{standard_schedule_str}'
        store_data(self.population, html, self.storage_dir, base_name)

    def persist_json(self, tmp_json, file_name) -> None:
        json_file = os.path.join(self.storage_dir, file_name)
        with open(json_file, 'w') as f:
            f.write(tmp_json)

    def retrieve_json(self, file_name) -> str:
        json_file = os.path.join(self.storage_dir, file_name)
        with open(json_file, 'r') as f:
            return f.read()

    def num_periods(self) -> int:
        return len(self.period_start_dates)

    def final_period_index(self) -> int:
        return self.num_periods() - 1

    def period_start_estimates(self, e: Employer, period_index: int) -> None:
        (dr_tmp_json, al_tmp_json) = e.make_estimates_and_return_data_to_persist(period_index)
        self.persist_json(dr_tmp_json, 'tmp_dr.json')
        self.persist_json(al_tmp_json, 'tmp_al.json')

    def period_end_calculations(self, e: Employer, period_index: int) -> None:
        tmp_dr_json = self.retrieve_json('tmp_dr.json')
        tmp_al_json = self.retrieve_json('tmp_al.json')
        return e.load_persisted_data_and_do_period_calculations(period_index, tmp_dr_json, tmp_al_json)

    def get_employer_instance(self):
        # Generate a dictionary needed to construct an instance of the Employer class
        # Hint: The json version of this is stored in the output directory of the run
        initializing_dict = self.get_initializing_dict()
        e = Employer(**initializing_dict)
        e.initialize()
        return e

    def process_period(self, period_index: int) -> None:
        e = self.get_employer_instance()
        if period_index == 0:
            self.period_start_estimates(e, period_index=period_index)
        if period_index == self.final_period_index()+1:
            score = self.period_end_calculations(e, period_index=period_index-1)
            self.store_reports(e.make_html_report())
            return score
        if period_index > 0 and period_index <= self.final_period_index():
            self.period_end_calculations(e, period_index=period_index-1)
            self.period_start_estimates(e, period_index=period_index)
            return 0
        return 0

    def run_like_veriport_would(self):
        score = 0
        for period_index in range(self.num_periods()+1):
            score += self.process_period(period_index)
        return score

    # def run_like_veriport_would_old(self):
    #     # Make the initial estimates for the employer
    #     e = self.get_employer_instance()
    #     self.period_start_estimates(e, period_index=0)

    #     # Now loop over the periods, for each period, we initialize a new employer
    #     # Then make the calculations, and the estimates for the next period,
    #     # persisting the data as we go
    #     for period_index in range(self.num_periods()-1):
    #         e = self.get_employer_instance()
    #         self.period_end_calculations(e, period_index=period_index)
    #         self.period_start_estimates(e, period_index=period_index+1)

    #     # Finally we calculate the final period's true values,
    #     # calculate our score and write the html report
    #     # returning the score
    #     e = self.get_employer_instance()
    #     score = self.period_end_calculations(e, period_index=self.final_period_index())
    #     self.store_reports(e.make_html_report())
    #     return score


def main() -> int:
    args = get_args()
    schedule = from_string_to_schedule(args.sch)
    filename = args.file

    if filename is not None:
        if not os.path.isfile(filename):
            print(f'Cannot open {filename}')
            return 0
        rm = run_man(schedule, args.dir, 'fixed_trials', filename, args.vp)
        return rm.run_like_veriport_would()

    i = 0
    errors = {}
    num_tests = min(args.iter, MAX_NUM_TESTS)
    while(i < num_tests):
        rm = run_man(schedule, args.dir, 'random_trials', '', False, i, args.mu, args.sig)
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
