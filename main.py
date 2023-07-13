# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from employer import Employer, Schedule

employer_json = {
    'start_count': '100',
    'pool_inception': '2023-02-01',
    'alcohol_percent': .1,
    'drug_percent': .5,
    'schedule': Schedule.QUARTERLY,
    # The rest can all be junk, as it gets overwritten in initialize
    'alcohol_administered': 0,
    'drug_administered': 0,
    'year': 2000,
    'employee_count': {'2023-01-01': 100},
    'period_start_dates': ['2023-01-01']
}


def main():
    e = Employer(**employer_json)
    e.initialize()
    e.randomize_employee_count(0, 2)
    e.pretty_print()


if __name__ == "__main__":
    main()
