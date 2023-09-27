# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

import argparse
import os

from schedule import Schedule
from data_persist import DataPersist
from random_population import population_dict_from_rand
from file_io import population_dict_from_file


MAX_NUM_TESTS = 500


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
    parser = argparse.ArgumentParser(
        description='Arguments: file_to_load, vp_format, output_directory'
        )
    parser.add_argument(
        '--file',
        type=str,
        help='data file to load'
        )
    parser.add_argument(
        '--dir',
        type=str,
        help='output directory',
        default='test_run'
        )
    parser.add_argument(
        '--sch',
        type=str,
        help='the testing schedule (MONTHLY, QUARTERLY, etc.)',
        default='quarterly'
        )
    parser.add_argument(
        '--vp',
        type=bool,
        help='Whether this comes from VP or from this program',
        default=True
        )
    parser.add_argument(
        '--iter',
        type=int,
        help='number of random iterations',
        default=4
        )
    parser.add_argument(
        '--mu',
        type=float,
        help='mu value of gaussian',
        default=0.01
        )
    parser.add_argument(
        '--sig',
        type=float,
        help='sigma value of gaussian',
        default=2.0
        )
    args = parser.parse_args()
    return args


def main() -> int:
    args = get_args()

    (schedule, base_dir, sub_dir, input_data_file, vp_format, random) = initialize_from_args(args)

    if not random:
        filename = args.file

        split_filepath = filename.split('/')
        base_name = os.path.splitext(split_filepath[-1])[0]

        population = population_dict_from_file(filename, vp_format)
        data_persist = DataPersist(
            schedule,
            population,
            base_dir,
            sub_dir,
            base_name,
            input_data_file,
            vp_format
            )
        return data_persist.run_like_veriport_would()

    i = 0
    errors = {}
    num_tests = min(args.iter, MAX_NUM_TESTS)
    while(i < num_tests):

        base_name = f'run_{i}'
        population = population_dict_from_rand(args.mu, args.sig)
        data_persist = DataPersist(
            schedule,
            population,
            base_dir,
            sub_dir,
            base_name,
            input_data_file,
            vp_format
            )
        err = data_persist.run_like_veriport_would()

        if err not in errors:
            errors[err] = []
        errors[err].append(i)
        i += 1

    for e in sorted(errors):
        print(
            f'level {e} errors: hit {len(errors[e])} errors out of {num_tests}: Runs: {errors[e]}'
            )

    return 0


if __name__ == "__main__":
    main()
