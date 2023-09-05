# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

import argparse

from file_io import write_population_to_vp_file
from random_population import generate_random_population_data


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Arguments: file path to write to, vp_format, mu, sigma')
    parser.add_argument('--fp', type=str, help='filepath to write output to')
    parser.add_argument('--vp', type=bool, help='Whether tp output in VP or native format', default=True)
    parser.add_argument('--mu', type=float, help='Gaussian mu parameter (data drift)', default=0.0)
    parser.add_argument('--sig', type=float, help='Gaussian sigma parameter (data spread)', default=0.0)
    args = parser.parse_args()
    return args


def main() -> int:
    args = get_args()

    mu = args.mu
    sigma = args.sig
    filepath = args.fp
    population = generate_random_population_data(mu, sigma)
    for d in population:
        print(f'{d}->{population[d]}')
    write_population_to_vp_file(population, filepath)


if __name__ == "__main__":
    main()
