from bisect import insort
from functools import total_ordering
from os import PathLike
from typing import Iterable, cast

import peewee as pw

database_connection = pw.SqliteDatabase("student_records.sqlite")


class DatabaseModelBase(pw.Model):
    class Meta:
        database = database_connection


@total_ordering
class Student(DatabaseModelBase):
    first = pw.TextField()
    middle = pw.TextField()
    last = pw.TextField()
    pouch = pw.IntegerField(unique=True)
    turned_in = pw.BooleanField()

    def turn_in(self):
        self.turned_in = True
        self.save()

    def get_pouch(self) -> int:
        p: int = cast(int, self.pouch)
        return p

    def change_pouch(self, new_number: int):
        self.pouch = new_number
        self.save()

    def get_name(self):
        if self.middle == "":
            return f"{self.first} {self.last}"
        return f"{self.first} {self.middle} {self.last}"

    def __repr__(self):
        return f"[{self.pouch}] {self.get_name()}"

    def __eq__(self, other):
        return self.last.__eq__(other.last)

    def __lt__(self, other):
        return self.last.__lt__(other.last)


class StudentRecord:
    students: dict[int, Student]
    student_list: list[Student]

    def __init__(self, students: Iterable[Student]):
        self.student_list = sorted(students)
        self.students = {s.get_pouch(): s for s in self.student_list}

    def __repr__(self):
        return ",".join(map(str, self.student_list))

    def add_student(self, first, middle, last, pouch, turned_in):
        s = Student()
        s.first = first
        s.middle = middle
        s.last = last
        s.pouch = pouch
        s.turned_in = turned_in
        s.save()

        insort(self.student_list, s)

    def turn_in(self, pouch_num):
        if pouch_num not in self.students:
            return None

        s = self.students[pouch_num]
        s.turned_in = True
        s.save()
        return s

    def set_turn_in_status(self, pouch: int, new_status: bool):
        if pouch not in self.student_list:
            return None

        s = self.students[pouch]
        s.turned_in = new_status
        s.save()
        return s

    @staticmethod
    def load_from_csv(fp: str) -> "StudentRecord":
        raise NotImplementedError("not implemented")

    @staticmethod
    def load_from_db(fp: str) -> "StudentRecord":
        raise NotImplementedError("not implmented")
