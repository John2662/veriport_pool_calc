# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from enum import Enum
from datetime import date


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


def trim_to_date(start_date: date, period_starts: list[date]) -> list[date]:
    period_start_list = [start_date]
    for d in period_starts:
        if d > start_date:
            period_start_list.append(d)
    return period_start_list


def construct_period_start_dates(inception: date, schedule: Schedule) -> list[date]:
    year = inception.year
    period_starts = []
    jan_1 = date(year=year, month=1, day=1)
    period_starts.append(jan_1)
    if schedule.num_periods == 1:
        return trim_to_date(inception, period_starts)

    if schedule.num_periods == 2:
        period_starts.append(date(year=year, month=7, day=1))
        return trim_to_date(inception, period_starts)

    if schedule.num_periods == 4:
        period_starts.append(date(year=year, month=4, day=1))
        period_starts.append(date(year=year, month=7, day=1))
        period_starts.append(date(year=year, month=10, day=1))
        return trim_to_date(inception, period_starts)

    if schedule.num_periods == 6:
        period_starts.append(date(year=year, month=3, day=1))
        period_starts.append(date(year=year, month=5, day=1))
        period_starts.append(date(year=year, month=7, day=1))
        period_starts.append(date(year=year, month=9, day=1))
        period_starts.append(date(year=year, month=11, day=1))
        return trim_to_date(inception, period_starts)

    if schedule.num_periods == 12:
        period_starts.append(date(year=year, month=2, day=1))
        period_starts.append(date(year=year, month=3, day=1))
        period_starts.append(date(year=year, month=4, day=1))
        period_starts.append(date(year=year, month=5, day=1))
        period_starts.append(date(year=year, month=6, day=1))
        period_starts.append(date(year=year, month=7, day=1))
        period_starts.append(date(year=year, month=8, day=1))
        period_starts.append(date(year=year, month=9, day=1))
        period_starts.append(date(year=year, month=10, day=1))
        period_starts.append(date(year=year, month=11, day=1))
        period_starts.append(date(year=year, month=12, day=1))
        return trim_to_date(inception, period_starts)

    if schedule.num_periods == 24:
        period_starts.append(date(year=year, month=1, day=1))
        period_starts.append(date(year=year, month=1, day=15))
        period_starts.append(date(year=year, month=2, day=1))
        period_starts.append(date(year=year, month=2, day=15))
        period_starts.append(date(year=year, month=3, day=1))
        period_starts.append(date(year=year, month=3, day=15))
        period_starts.append(date(year=year, month=4, day=1))
        period_starts.append(date(year=year, month=4, day=15))
        period_starts.append(date(year=year, month=5, day=1))
        period_starts.append(date(year=year, month=5, day=15))
        period_starts.append(date(year=year, month=6, day=1))
        period_starts.append(date(year=year, month=6, day=15))
        period_starts.append(date(year=year, month=7, day=1))
        period_starts.append(date(year=year, month=7, day=15))
        period_starts.append(date(year=year, month=8, day=1))
        period_starts.append(date(year=year, month=8, day=15))
        period_starts.append(date(year=year, month=9, day=1))
        period_starts.append(date(year=year, month=9, day=15))
        period_starts.append(date(year=year, month=10, day=1))
        period_starts.append(date(year=year, month=10, day=15))
        period_starts.append(date(year=year, month=11, day=1))
        period_starts.append(date(year=year, month=11, day=15))
        period_starts.append(date(year=year, month=12, day=1))
        period_starts.append(date(year=year, month=12, day=15))
        return trim_to_date(inception, period_starts)

    return []
