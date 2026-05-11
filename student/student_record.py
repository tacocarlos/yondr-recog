import peewee as pw
from _typeshed import FileDescriptorOrPath, StrOrBytesPath


class StudentRecord:
    def __init__(self, db_path: StrOrBytesPath):
        self.local_db = {}
        self.db: pw.SqliteDatabase = pw.SqliteDatabase(db_path)

    class Student(pw.Model):
        class Meta:
            database =
        def __init__(self, first, middle, last, pouch, turned_in=False):
            self.first = first
            self.middle = middle
            self.last = last
            self.pouch = pouch
            self.turned_in = False

        def turn_in(self):
            self.turned_in = True

        def set_turned_in(self, t: bool):
            self.turned_in = t

        def __hash__(self):
            return hash(f"{self.first} {self.middle} {self.last}")

        def __repr__(self):
            return f"({self.first} {self.middle} {self.last}) -> [{self.pouch}, {self.turned_in}]"



    @staticmethod
    def load_csv(fd: FileDescriptorOrPath):
