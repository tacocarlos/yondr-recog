import csv
from bisect import insort
from functools import total_ordering
from tkinter.simpledialog import askinteger
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
    pouch = pw.TextField(unique=True)
    turned_in = pw.BooleanField()
    grade = pw.IntegerField()

    def _apply_change(self):
        s = Student.get_by_id(self.get_id())
        s.first = self.first
        s.middle = self.middle
        s.last = self.last
        s.pouch = self.pouch
        s.turned_in = self.turned_in
        s.grade = self.grade
        s.save()
        self = s
        return s

    @staticmethod
    def from_query(tuple):
        first, middle, last, pouch, turned_in, grade = tuple
        s = Student()
        s.first = first
        s.middle = middle
        s.last = last
        s.turned_in = turned_in
        s.pouch = pouch
        s.grade = grade
        return s

    def check_out(self):
        self.turned_in = False
        return self._apply_change()

    def turn_in(self):
        self.turned_in = True
        return self._apply_change()

    def toggle_turn_in(self):
        self.turned_in = not self.turned_in
        return self._apply_change()

    def get_pouch(self) -> str:
        p: str = cast(str, self.pouch)
        return p

    def change_pouch(self, new_number: str):
        self.pouch = new_number
        return self._apply_change()

    def get_name(self):
        if self.middle == "":
            return f"{self.first} {self.last}"
        return f"{self.first} {self.middle} {self.last}"

    def turned_in_badge(self) -> str:
        """Returns a checkmark character when the pouch has been turned in, otherwise an empty string."""
        return "\u2713" if self.turned_in else ""

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f"[{self.pouch}] {self.get_name()}"

    def __eq__(self, other):
        last = self.last.__eq__(other.last)
        f = self.first.__eq__(other.first)
        m = self.middle.__eq__(other.middle)

        return last and f and m

    def __lt__(self, other):
        return self.last.__lt__(other.last)


class StudentRecord:
    students: dict[str, Student]
    student_list: list[Student]

    def __init__(self, students: Iterable[Student]):
        self.student_list = sorted(students)
        self.students = {s.get_pouch(): s for s in self.student_list}

    def __repr__(self):
        return ",".join(map(str, self.student_list))

    def _pouch_is_used(self, p):
        s = Student.get_or_none(pouch=p)
        return s is not None

    def register_student(self, s: Student):
        insort(self.student_list, s)
        self.students[s.get_pouch()] = s

    def add_student(
        self,
        first,
        middle,
        last,
        pouch,
        grade: int,
        turned_in: bool = False,
        apply_update: bool = False,
    ):
        if self._pouch_is_used(pouch):
            return None

        s, was_created = Student.get_or_create(
            first=first,
            middle=middle,
            last=last,
            defaults={
                "first": first,
                "middle": middle,
                "last": last,
                "pouch": pouch,
                "grade": grade,
                "turned_in": turned_in,
            },
        )
        print(f"Was created: {was_created}")
        print(type(s), s)
        self.register_student(s)
        return s

    def remove_student(self, s: Student):
        self.student_list.remove(s)
        self.students.pop(s.get_pouch())
        s.delete()

    def toggle(self, pouch_num):
        if pouch_num not in self.students:
            return

        s = self.students[pouch_num]
        s.toggle_turn_in()

    def check_out(self, pouch_num):
        if pouch_num not in self.students:
            return False

        s = self.students[pouch_num]
        s.check_out()
        return s

    def turn_in(self, pouch_num: str):
        if pouch_num not in self.students:
            return None

        s = self.students[pouch_num]
        s.turn_in()
        return s

    def set_turn_in_status(self, pouch: str, new_status: bool):
        if pouch not in self.students:
            return None

        s = self.students[pouch]
        if new_status:
            s.turn_in()
        else:
            s.check_out()
        return s

    def change_pouch(self, old_pouch: str, new_pouch: str):
        if old_pouch not in self.students:
            return False

        s = self.students.pop(old_pouch)
        s.pouch = new_pouch
        self.students[new_pouch] = s
        s._apply_change()
        return s

    @staticmethod
    def load_from_csv(fp: str) -> "StudentRecord":
        sr = StudentRecord([])
        with open(fp, mode="r") as file:
            for line in file.readlines():
                line = "".join([c for c in line if c.isprintable()])
                if line.strip() == "":
                    continue
                grade = -1
                first, middle, last, pouch = ["", "", "", ""]
                turned_in = False
                for i, p in enumerate(line.split(",")):
                    if i == 0:
                        grade = int(p)
                    elif i == 1:
                        first = p
                    elif i == 2:
                        last = p
                    elif i == 3:
                        middle = p
                    elif i == 4:
                        pouch = p
                    elif i == 5:
                        if p.lower() == "yes":
                            turned_in = True
                print(first, middle, last, pouch, turned_in)
                s = sr.add_student(first, middle, last, pouch, grade, turned_in)
                while s is None:
                    revised_p = askinteger(
                        "Pouch Collision",
                        f"Pouch number {pouch} is already in use. Please provide a different pouch number.",
                    )
                    if revised_p is None:
                        continue
                    pouch = revised_p
                    s = sr.add_student(first, middle, last, pouch, grade, turned_in)

                print(f"Added {s}")
        return sr

    @staticmethod
    def load_from_db(fp: str) -> "StudentRecord":
        sr = StudentRecord([])
        for sq in Student.select():
            s = sr.register_student(sq)
            # s = sr.add_student(
            # sq.first, sq.middle, sq.last, sq.pouch, sq.grade, sq.turned_in
            # )
            print(f"Added {s}")
        return sr

    def export_csv(self, fp: str):
        with open(fp, mode="w") as file:
            writer = csv.writer(file)
            for pouch, s in self.students.items():
                writer.writerow(
                    [
                        s.grade,
                        s.last,
                        s.first,
                        s.middle,
                        pouch,
                        "Yes" if s.turned_in else "No",
                    ]
                )


database_connection.create_tables([Student])
