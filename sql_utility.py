"""
The SQLUtility interacts with the SQLite database.

Functions:
----------
On LiftLog startup:
- gets imports to display in the Imports tab
- gets exercise/sets dictionary

On import:
- insert DailySets objects and Import object into database

On deletion/undo of import:
- delete Import object and associated DailySets objects from database
"""

import math
import sqlite3
from datetime import date
from typing import Dict

from exercise_set import ExerciseSet


def create_tables():
    """
    Create tables in SQLite if they don't already exist. There are no primary
    keys because SQLite automatically creates the ROWID field for every item.
    """
    con = sqlite3.connect("personal.db")
    cur = con.cursor()
    # date is stored in SQLite as TEXT (YYYY-MM-DD).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_sets(
            exercise TEXT,
            date TEXT,
            string TEXT,
            import_id INTEGER
        )
    """)
    # date_time is stored in SQLite as TEXT (YYYY-MM-DD HH:MM:SS).
    # file is the content of the file used for the import (ex: HTML file content)
    # method is TEXT that equals 'html' or 'apple'
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import(
            date_time TEXT,
            file TEXT,
            method TEXT
        )
    """)

    cur.close()
    con.close()


class SQLUtility():
    def __init__(self):
        create_tables()

        self.imports_list = self.get_imports()
        self.exercise_sets_dict = {}

    def get_imports(self):
        """Retrieve imports from SQLite, and return them as a list of tuples."""
        con = sqlite3.connect("personal.db")
        cur = con.cursor()
        result = cur.execute("SELECT * FROM import")
        imports = result.fetchall()
        cur.close()
        con.close()
        return imports

    def get_exercise_sets_dict(self):
        """
        Retrieve daily_sets items from SQLite, convert them into ExerciseSet
        objects in Python, and build a dictionary that maps exercises to
        ExerciseSet objects.
        """
        con = sqlite3.connect("personal.db")
        cur = con.cursor()
        exercise_sets_dict = {}

        result = cur.execute("SELECT exercise, date, string FROM daily_sets")
        all_daily_sets_items = result.fetchall()
        for item in all_daily_sets_items:
            # Convert daily_sets in SQLite to ExerciseSet objects in Python
            individual_exercise_sets = self.parse_sets(item)

            # Now add those ExerciseSet objects to the dict.
            if individual_exercise_sets:
                if len(individual_exercise_sets) > 6:
                    print("WARNING, LOTS OF SETS FOUND")
                exercise = item[0]
                if exercise not in self.exercise_sets_dict:
                    self.exercise_sets_dict[exercise] = individual_exercise_sets
                else:
                    self.exercise_sets_dict[exercise] += individual_exercise_sets

                # try:
                #     ex_sets = self.parse_sets(exercise, sets_str, curr_date)
                #
                # except ValueError:
                #     print("ABORTING REST OF LINE BECAUSE OF VALUEERROR.")

        cur.close()
        con.close()
        return exercise_sets_dict

    def parse_sets(self, daily_sets_item : tuple [str, str, str]):
        """
        Given a daily_sets item from SQLite, return a list of ExerciseSet objects.
        :return: all ExerciseSet objects that can be parsed from the daily_set item.
        """
        exercise, date_str, sets_str = daily_sets_item
        y, m, d = [int(p) for p in date_str.split('-')]
        date_of_sets = date(year=y, month=m, day=d)
        print(f"Parsing sets, exercise='{exercise}' sets_str='{sets_str}'")
        if sets_str.__contains__('@'):
            # Parse a sets with weight
            return self.parse_weighted_sets(exercise, sets_str, date_of_sets)
        else:
            # Parse bodyweight sets
            return self.get_exercise_sets(exercise, 0, sets_str, date_of_sets)

    def parse_weighted_sets(self, exercise: str, sets_str: str, date_of_sets: date):
        """
        Given all the components of a daily_sets item, get a list of ExerciseSet
        objects. This function parses the sets_str, delimits it by setsxreps +
        wt pairs, and calls get_exercise_sets.

        :param exercise:      example: 'bench'
        :param sets_str:      example: '10@65,~8@70,5+1@75,4,5@80,2x3@85,2x2,~1@90'
        :param date_of_sets:  example: 2025/05/27
        :return:  all ExerciseSet objects that can be parsed from the inputs.
        """
        exercise_sets = []

        # Split sets_str into a list with format [setsxreps, wt, setsxreps, wt, ... ]  # TODO it might be nice to use tuples
        # first_split format:  ['10', '65', '~8', '70,5+1', '75,4,5', '80,2x3', '85,2x2,~1', '90']
        # second_split format: ['10', '65', '~8', '70', '5+1', '75', '4,5', '80', '2x3', '85', '2x2,~1', '90']
        first_split = sets_str.split("@")
        second_split = [first_split[0]]
        for part in first_split[1:]:  # don't split by comma for the first item. The first item always indicates reps (not weight)
            subparts = part.split(',', maxsplit=1)
            for subpart in subparts:
                second_split.append(subpart)

        # At this point, second_split should have 'setsxreps' 'weight' ... repeated
        # We'll consider other formats malformed for now. Maybe this could be handled more gracefully later...
        if len(second_split) % 2 != 0:
            print(f"SKIPPING, THIS SET STRING HAS INVALID SYNTAX.")
            return []

        for i in range(0, len(second_split), 2):
            the_sets = second_split[i]  # '10' '~8' ... '2x2,~1'
            try:
                weight = float(second_split[i + 1])  # 65 70 ... 90
            except ValueError:
                print(f"SKIPPING, FAILED TO PARSE WEIGHT: {second_split[i]}@{second_split[i + 1]}")
                continue
            print(f"  {the_sets}@{weight}")
            exercise_sets += self.get_exercise_sets(exercise, weight, the_sets, date_of_sets)

        return exercise_sets


    def get_exercise_sets(self, exercise: str, weight: float, the_sets: str, date_of_sets: date):
        """
        Given an exercise, weight, and string of the sets performed at that weight,
        create ExerciseSet objects.
        :param exercise:      example: 'bench'
        :param weight:        example: 90.0
        :param the_sets:      example: '2x10,~9'
        :param date_of_sets:  example: 2025/05/27
        :return: list of ExerciseSet objects
        """
        exercise_sets = []

        for the_set in the_sets.split(","):
            # Check for 'x', which indicates multiple sets with the same reps
            if the_set.__contains__('x'):  # ex: '2x10'
                setsxreps = the_set.split('x')
                num_sets = int(setsxreps[0])
                reps = setsxreps[1]
            else:  # ex: '9'
                num_sets = 1
                reps = the_set

            # Account for '~' (partial reps)
            partial_reps = reps.__contains__('~')
            reps.replace('~', '')

            # Account for '+' (disjoint reps).  ex: 5+1 => 6
            # Also, account for half reps indicated by decimal point. ex: 4.5 => 4
            num_reps = sum([math.trunc(float(r)) for r in reps.split('+')])  # "5+1" = 6

            if num_reps > 100:
                print(f"WARNING, suspiciously high number of reps {num_reps}.")
                print("These sets won't be added.")
                break

            for i in range(num_sets):
                s = ExerciseSet(exercise=exercise, reps=num_reps, weight=weight, partial_reps=partial_reps, date=date_of_sets)
                print(f"    {s}")
                exercise_sets.append(s)

        return exercise_sets

# Temporary Testing Area
if __name__ == '__main__':
    con = sqlite3.connect("personal.db")
    cur = con.cursor()

    with open('my_workouts_lite.html') as f:
        content = f.read()
        print(content)
        cur.execute(f"INSERT INTO import(date_time, file, method) VALUES('2025-05-27', '{content}', 'html')")
        con.commit()

    cur.close()
    con.close()


    sql_utility = SQLUtility()
    print(sql_utility.imports_list)
    print(sql_utility.exercise_sets_dict)
