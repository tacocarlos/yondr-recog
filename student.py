import csv


def nameStr(x: str):
    return x[0].upper() + x[1:].lower()


class Student:
    def __init__(self, first, middle, last, pouch_num):
        self.first = first
        self.middle = middle
        self.last = last
        self.pouch_num = pouch_num
        self.turned_in = False

    def get_pouch(self):
        return self.pouch_num

    def turn_in(self):
        self.turned_in = True

    def __str__(self):
        return f"[{3:pouch_num}] {nameStr(self.first)} {nameStr(self.middle)} {nameStr(self.last)}"

    def __hash__(self):
        return hash(self.pouch_num)


class StudentList:
    def __init__(self, students: list[Student]):
        self.db: dict[int, Student] = {s.pouch_num: s for s in students}

    def add_student(self, s: Student) -> bool:
        self.db[s.pouch_num] = s
        return s.pouch_num in self.db

    def turn_in(self, pouch_num: int) -> Student | None:
        s = self.get_student(pouch_num)
        if s is None:
            return None

        s.turn_in()
        return s

    @staticmethod
    def load(csv_path: str) -> "StudentList":
        sl = StudentList([])
        with open(csv_path, mode="r") as file:
            for line in file.readlines():
                parts = line.split(",")
                (
                    first,
                    middle,
                    last,
                ) = ""
                pouch_num = -1
                status = False
                for i in range(len(parts)):
                    if i == 0:
                        first = parts[0]
                    elif i == 1:
                        last = parts[1]
                    elif i == 2:
                        middle = parts[2]
                    elif i == 3:
                        tok = parts[3]
                        if tok.isnumeric():
                            pouch_num = int(tok)
                        else:
                            status = bool(parts[3])
                    elif i == 4:
                        status = int(parts[4])

                s = Student(first, middle, last, pouch_num)
                if status:
                    s.turn_in()
                sl.add_student(s)

        return sl

    def save(self, csv_path: str) -> None:
        with open(csv_path, mode="w") as file:
            writer = csv.writer(file)
            for pouch, s in self.db.items():
                writer.writerow([s.last, s.first, s.middle, pouch, s.turned_in])

    def get_student(self, pouch_num: int) -> Student | None:
        return self.db.get(pouch_num)
