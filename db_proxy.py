# Copyright (C) Colibri Software, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by John Read <john.read@colibri-software.com>, July 2023

from datetime import timedelta, date
from pydantic import BaseModel


class DbConn(BaseModel):
    population: dict

    def __str__(self) -> str:
        return str(self.population)

    @property
    def get_inception_date(self):
        return list(self.population.keys())[0]

    def get_population_report(self, start: date, end: date) -> list[int]:
        requested_population = []
        while start <= end:
            requested_population.append(self.employee_count(start))
            start += timedelta(days=1)
        return requested_population

    def employee_count(self, day: date) -> int:
        return self.population[day]

    @staticmethod
    def extract_date(s: str) -> date:
        s = s.strip().replace('\'', '')
        [y, m, d] = s.split('-')
        y = int(y)
        m = int(m)
        d = int(d)
        return date(year=y, month=m, day=d)

    @staticmethod
    def from_initialization_string(m_str: str) -> dict:
        dic = {}
        dic_array = m_str[1:-1].split(',')
        for item in dic_array:
            [d, v] = item.split(':')
            d = DbConn.extract_date(d)
            try:
                v = int(v)
            except ValueError:
                print(f'{str(d)=} <-> {v}')
                exit(0)
            dic[d] = v
        return dic

    @staticmethod
    def to_initialization_string(dic: dict) -> str:
        '''
        This takes a population dictionary and converts it into a string of the form
        self.db_str="{'1963-12-28': 10, '1963-12-29': 50, '1963-12-30': 100, '1963-12-31': 101}"
        which passed to the Employer (attached to db_str) from main. The Employer
        calls the inverse method to get a map back which is passed int the constructor
        '''
        s_dic = {}
        for d in dic:
            s_dic[str(d)] = dic[d]
        return str(s_dic)

    @staticmethod
    def generate_object(pop_dict: dict):  # -> DbConn:
        db_conn = DbConn(**pop_dict)
        return db_conn
