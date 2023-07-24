# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
from pydantic import BaseModel


class DbConn(BaseModel):
    population: dict

    def get_population_report(self, start: date, end: date) -> list[int]:
        requested_population = []
        while start <= end:
            requested_population.append(self.employee_count(start))
            start += timedelta(days=1)
        return requested_population

    def employee_count(self, day: date) -> int:
        return self.population[day]

    def validate_data(self) -> bool:
        return population_valid(self.population)

    def data_as_string_array(self) -> list[str]:
        s = []
        for d in self.population:
            s.append(f'{str(d)} -> {self.population[d]}')
        return s


def population_valid(population) -> bool:
    for d in population:
        if population[d] < 0:
            print(f'On {str(d)} population is {population[d]} < 0')
            return False
    return True
