# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import date, timedelta
from random import randint
import random

MAX_POP = 500


# not completly random if the year is a leap year
def get_random_date(year: int = 0, month: int = 0, day: int = 0) -> str:
    if year > 1900 and month > 0 and month <= 12 and day > 0 and day <= 31:
        return str(date(year=year, month=month, day=day))
    days = randint(0, 364)
    year = 2016 + randint(0, 10)
    return date(year=year, month=1, day=1) + timedelta(days=days)


def get_random_population(pop: int = 0) -> int:
    if pop <= 0:
        return randint(1, MAX_POP)
    return pop


def calculate_population_change(d, mu, sigma: float) -> int:
    if abs(sigma) < 0.000001:
        return 0
    if d.weekday() < 5:
        return int(random.gauss(mu, sigma))
    return 0


def order_correctly(start: date, end: date) -> tuple:
    if start > end:
        tmp = end
        end = start
        start = tmp
    return start, end


def increment(day: date) -> date:
    oneday = timedelta(days=1)
    return day+oneday


def generate_population(
        start: date,
        end: date,
        pop: int,
        mu: float = 0.0,
        sigma: float = 0
        ) -> dict:
    (start, end) = order_correctly(start, end)
    pop = max(0, pop)
    population = {}
    day = start
    population[start] = pop
    while day < end:
        day = increment(day)
        pop += calculate_population_change(day, mu, sigma)
        pop = max(0, pop)
        population[day] = pop
    return population


def generate_random_population_data(mu: float, sigma: float):
    pop = get_random_population()
    start = get_random_date()
    end = date(year=start.year, month=12, day=31)
    return generate_population(start, end, pop, mu, sigma)


def population_dict_from_rand(mu: float, sigma: float) -> dict:
    return generate_random_population_data(mu, sigma)
