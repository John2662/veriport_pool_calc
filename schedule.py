# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from enum import Enum


class Schedule(int, Enum):
    # For weekly: skip first and last weeks of the year
    # so for example, the first period will contain up to two full weeks
    # ending on a sunday (on or before Jan 14)

    # WEEKLY = 50
    SEMIMONTHLY = 24
    MONTHLY = 12
    BIMONTHLY = 6
    QUARTERLY = 4
    SEMIANNUALLY = 2
    ANNUALLY = 1
    CUSTOM = 0

    @staticmethod
    def as_str(value):
        # if value == Schedule.WEEKLY:
        #     return 'weekly'
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
