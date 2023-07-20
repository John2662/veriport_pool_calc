# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date, datetime
from pydantic import BaseModel
import json
import random


class DbConn(BaseModel):
    population: dict
    # datafile: str

    def __str__(self) -> str:
        return str(self.population)

    def get_population_report(self, start: date, end: date) -> list[int]:
        requested_population = []
        while start <= end:
            requested_population.append(self.employee_count(start))
            start = DbConn.increment(start)
        return requested_population

    def employee_count(self, day: date) -> int:
        return self.population[day]

    @staticmethod
    def generate_object(json_str: str) -> tuple:
        d_dict = json.loads(json_str)
        (generate_dict, pool_inception) = DbConn.extract_initiation_json(d_dict)
        db_conn = DbConn(**generate_dict)
        return (db_conn, pool_inception)



#################################################
    @staticmethod
    def string_to_date(s):
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except:
            return None

    @staticmethod
    def calculate_population_change(d, mu, sigma: float) -> int:
        if abs(sigma) < 0.000001:
            return 0
        if d.weekday() < 5:
            return int(random.gauss(mu, sigma))
        return 0

    @staticmethod
    def order_correctly(start: date, end: date) -> tuple:
        if start > end:
            tmp = end
            end = start
            start = tmp
        return start, end

    @staticmethod
    def increment(day: date) -> date:
        oneday = timedelta(days=1)
        return day+oneday

    @staticmethod
    def generate_population(start: date, end: date, pop: int, mu: float = 0.0, sigma: float = 0) -> dict:
        (start, end) = DbConn.order_correctly(start, end)
        pop = max(0, pop)
        population = {}
        day = start
        population[start] = pop
        while day < end:
            day = DbConn.increment(day)
            pop += DbConn.calculate_population_change(day, mu, sigma)
            pop = max(0, pop)
            population[day] = pop
        return population

    @staticmethod
    def extract_initiation_json(d_dict: dict) -> tuple:
        start = d_dict['start'] if 'start' in d_dict else None
        pop = d_dict['pop'] if 'pop' in d_dict else None
        if start is None or pop is None:
            return None

        try:
            start = DbConn.string_to_date(start)
            pop = int(pop)
        except ValueError:
            return None

        pop = max(0, pop)
        pool_inception = start

        end = date(year=start.year, month=12, day=31)
        mu = d_dict['mu'] if 'mu' in d_dict else 0
        sigma = d_dict['sigma'] if 'sigma' in d_dict else 0

        try:
            mu = float(mu)
            sigma = int(sigma)
        except ValueError:
            mu = 0
            sigma = 0

        population = DbConn.generate_population(start, end, pop, mu, sigma)
        return ({'population': population}, pool_inception)

#################################################
