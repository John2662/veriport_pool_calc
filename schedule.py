# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from enum import Enum


class Schedule(int, Enum):
    SEMIMONTHLY = 24
    MONTHLY = 12
    BIMONTHLY = 6
    QUARTERLY = 4
    SEMIANNUALLY = 2
    ANNUALLY = 1

    @property
    def num_periods(self) -> int:
        return int(self)

    @property
    def final_period_index(self) -> int:
        return self.num_periods - 1

    @staticmethod
    def as_str(value):
        if value == Schedule.SEMIMONTHLY:
            return 'semi-monthly'
        if value == Schedule.MONTHLY:
            return 'monthly'
        if value == Schedule.BIMONTHLY:
            return 'bi-monthly'
        if value == Schedule.QUARTERLY:
            return 'quarterly'
        if value == Schedule.SEMIANNUALLY:
            return 'semiannually'
        if value == Schedule.ANNUALLY:
            return 'annually'
        return 'custom'

    @staticmethod
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

    @staticmethod
    def from_int_to_schedule(i):
        if i == 24:
            return Schedule.SEMIMONTHLY
        if i == 12:
            return Schedule.MONTHLY
        if i == 6:
            return Schedule.BIMONTHLY
        if i == 4:
            return Schedule.QUARTERLY
        if i == 2:
            return Schedule.SEMIANNUALLY
        if i == 1:
            return Schedule.ANNUALLY
        print('hit default: QUARTERLY')
        return Schedule.QUARTERLY
