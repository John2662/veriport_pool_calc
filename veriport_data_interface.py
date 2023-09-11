# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

import argparse
import os
import json

from schedule import Schedule
from calculator import get_calculator_instance
from initialize_json import compile_json

class VeriportDataInterface:

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
