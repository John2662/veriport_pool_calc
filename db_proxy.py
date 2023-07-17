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

    def __str__(self):
        return str(self.population)

    @staticmethod
    def calculate_population_change(d, mu, sigma: int):
        if sigma == 0:
            return 0
        if d.weekday() < 5:
            return int(random.gauss(mu, sigma))
        return 0

    @staticmethod
    def order_correctly(start: date, end: date):
        if start > end:
            tmp = end
            end = start
            start = tmp
        return start, end

    @staticmethod
    def increment(day: date):
        oneday = timedelta(days=1)
        return day+oneday

    @staticmethod
    def generate_population(start: date, end: date, pop: int, mu: float = 0.0, sigma: int = 0):
        start, end = DbConn.order_correctly(start, end)
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
    def generate_object(json_str: str):
        d_dict = json.loads(json_str)
        print(f'{d_dict=}')
        filename = d_dict['filename'] if 'filename' in d_dict else None

        if filename is not None:
            # load dic from file and create object
            population = DbConn.read_population_from_file(filename)
            generate_dict = {'population': population}
            return DbConn(**generate_dict)

        start = d_dict['start'] if 'start' in d_dict else None
        pop = d_dict['pop'] if 'pop' in d_dict else None
        if start is None or pop is None:
            return None

        try:
            start = datetime.strptime(start, '%Y-%m-%d').date()
            pop = int(pop)
        except ValueError:
            return None

        pop = max(0, pop)

        # This is a bit kludgy, since the employer should know this!
        pool_inception = start
        start_count = pop

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
        generate_dict = {'population': population}
        db_conn = DbConn(**generate_dict)
        db_conn.write_population_to_file('pop_dump.csv')
        return db_conn, pool_inception, start_count

    @staticmethod
    def read_population_from_file():
        # TODO write this method
        population = {}
        return population

    def write_population_to_file(self, filename: str):
        # TODO write this method
        pass

    def load_population(self, start: date, end: date):
        requested_population = []
        while start <= end:
            requested_population.append(self.employee_count(start))
            start = DbConn.increment(start)
        return requested_population

    def employee_count(self, day: date):
        return self.population[day]

    def average_population(self, start: date, end: date):
        day, end = DbConn.order_correctly(start, end)
        num_days = (end-day).days + 1
        count = 0
        while day <= end:
            count += self.population[day]
            day = DbConn.increment(day)
        return float(count) / float(num_days)
