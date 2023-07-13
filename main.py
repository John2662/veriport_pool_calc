# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Employer, employer_json


def main():
    e = Employer(**employer_json)
    e.initialize()
    e.randomize_employee_count(0, 2)
    e.pretty_print()


if __name__ == "__main__":
    main()
