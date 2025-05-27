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
from datetime import datetime
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
        print("\nBuilding Exercise-Sets Dictionary")
        con = sqlite3.connect("personal.db")
        cur = con.cursor()
        exercise_sets_dict = {}

        result = cur.execute("SELECT exercise, date, string FROM daily_sets")
        all_daily_sets_items = result.fetchall()
        for item in all_daily_sets_items:
            print(f'Got an item: {item}')
            # Convert daily_sets in SQLite to ExerciseSet objects in Python
            individual_exercise_sets = self.parse_sets(item)

            # Now add those ExerciseSet objects to the dict.
            if individual_exercise_sets:
                if len(individual_exercise_sets) > 6:
                    print("WARNING, LOTS OF SETS FOUND")
                exercise = item[0]
                if exercise not in exercise_sets_dict:
                    exercise_sets_dict[exercise] = individual_exercise_sets
                else:
                    exercise_sets_dict[exercise] += individual_exercise_sets

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
                print(f"  {the_sets}@{weight}")
                exercise_sets += self.get_exercise_sets(exercise, weight, the_sets, date_of_sets)
            except ValueError:
                print(f"SKIPPING MALFORMED LINE. Double check weight or syntax: {second_split[i]}@{second_split[i + 1]}")
                continue


        return exercise_sets


    def get_exercise_sets(self, exercise: str, weight: float, the_sets: str, date_of_sets: date):
        """
        This is the method that actually returns the ExerciseSet objects.
        It takes various components of a daily_sets item.
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

    def import_sets_via_html(self, html_filepath, alias_filepath):
        alias_dict = self.parse_alias_file(alias_filepath)

        con = sqlite3.connect("personal.db")
        cur = con.cursor()

        daily_sets_list = []
        print(f"IMPORTING {html_filepath}")

        with open(html_filepath, 'r') as f:
            content = f.read()
            # TODO check if content matches the content of a previous import, and ask the user if they want to proceed.

        with open(html_filepath, 'r') as f:
            parsing_exercises = False
            # curr_date = date.today()  # temp value

            for line_num, line in enumerate(f.readlines(), start=1):
                line = line.lower().strip()
                if line.__contains__("<body>"):
                    parsing_exercises = True
                elif line.__contains__("</body>"):
                    parsing_exercises = False

                if parsing_exercises:
                    # h2 always contains the date
                    if line.__contains__("<h2>"):
                        try:
                            # Remove h2 tags, and split at the first space.
                            # This should leave the date part of the string, which
                            # can be split by / to get M,D,Y
                            date_part = line[len("<h2>"): len(line) - len("</h2>")].split(" ")[0]
                            month, day, year = [int(item) for item in date_part.split("/", 3)]
                            if year < 2000:  # Sometimes year is formatted with only two digits.
                                year += 2000
                            curr_date = date(year, month, day)
                            print(f"\nCURR DATE: {curr_date}")
                        except ValueError:
                            print(
                                f"\nFAILED TO PARSE DATE FROM {line_num}. line='{line}'  date_part='{date_part}'")

                    # Lines with exercises are structured like this: "exercise : sets"
                    elif line.__contains__(':'):
                        print(line_num, line)
                        exercise = self.parse_exercise(line, alias_dict)

                        sets_str = self.sanitize_sets(line[line.index(':'):])
                        if sets_str == "":
                            print("SKIPPING, NO SETS TO LOG.")
                        else:
                            daily_sets_item = (exercise, curr_date, sets_str)
                            print(f'  daily sets found: {daily_sets_item}')
                            daily_sets_list.append(daily_sets_item)

        cur.execute("BEGIN TRANSACTION")

        # Insert import item
        now = datetime.today()
        now_str = f"{now.year}/{now.month}/{now.day} {now.hour}:{now.minute}:{now.second}"
        cur.execute(f"INSERT INTO import(date_time, file, method) VALUES('{now_str}', '{content}', 'html')")

        # Insert daily_sets items
        import_id = cur.lastrowid
        print(f"\ntime to insert: {daily_sets_list}")
        cur.executemany(f"INSERT INTO daily_sets(exercise, date, string, import_id) VALUES (?, ?, ?, {import_id})", daily_sets_list)

        con.commit()
        cur.close()
        con.close()

    def parse_alias_file(self, alias_filepath: str):
        """Parse alias txt file, and populate the alias dictionary."""
        result = {}
        with open(alias_filepath, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line.startswith('#') or line == '':
                    continue
                elif line.startswith('.'):
                    curr_common_name = line[1:]
                else:
                    result[line] = curr_common_name
        return result

    def parse_exercise(self, ln: str, alias_dict: Dict) -> str:
        """
        Parse exercise from a line in an HTML file.
        :param ln: line in a workout file.   Ex: <li>Rear delt rows SS1 : 3x15 at 12.5<br></li>
        :return:  exercise name in the line. Ex: 'rear delt row'
        """
        result = ln.split(':')[0]

        # First characters in the line are "<li>" or "<div>", which can be ignored
        result = result[result.index('>') + 1:]

        # Ignore anything between parenthesis
        if result.__contains__('('):
            opening_paren = result.index('(')
            try:
                closing_paren = result.rindex(')')  # use rindex in case the line contains multiple sets of parenthesis
                result = result[:opening_paren] + result[closing_paren + 1:]
            except ValueError:
                result = result[:opening_paren]

        # ' ss[0-9]' indicates the exercise was performed as a superset.
        # This is irrelevant to the exercise and can be ignored.
        if result.__contains__(' ss'):
            result = result[:result.index(' ss')]

        # Some characters can be safely removed without obscuring the exercise's meaning
        result = result.replace('-', '')
        result = result.replace('’', '')
        result = result.replace('.', '')

        # Some manual replacement.
        result = result.replace(';', ',')
        result = result.replace('barbell', 'bb')
        result = result.replace('dumbbell', 'db')
        result = result.replace('ez bar', 'ezbar')
        result = result.replace('t bar', 'tbar')
        result = result.replace('hex bar', 'hexbar')
        result = result.replace('hexbar', 'hb')
        # Going with singular names instead of plural for now.
        # TODO Probably want a better way of aliasing exercises.
        result = result.replace('triceps', 'tricep')
        result = result.replace('tricep', 'tri')
        result = result.replace('curls', 'curl')
        result = result.replace('rows', 'row')
        result = result.replace('ups', 'up')
        result = result.replace('downs', 'down')
        result = result.replace('extensions', 'extension')
        result = result.replace('kickbacks', 'kickback')
        result = result.replace('raises', 'raise')
        result = result.replace('hangs', 'hang')
        result = result.replace('deadlifts', 'deadlift')

        result = result.strip()

        # Check if this exercise is in the alias dict. If so, use the common name
        if result in alias_dict.keys():
            # print("UseAlias")
            result = alias_dict[result]
        # else:
        #     print("DontAlias")
        return result


    def sanitize_sets(self, ln: str) -> str:
        """
        Given the portion of a workout line indicating the sets, strip comments and
        undesirable characters.
        :param ln: raw string of exercise sets.  Ex:  12 at 60, 2x9 at 70<br></li>
        :return: sanitized sets string.          Ex: 12@60,2x9@70
        """
        # Skip drop sets (for now?)
        if ln.__contains__('drop'):
            return ""

        result = ""
        ln = ln.replace('at', '@')
        ln = ln.replace(';', ',')
        valid_chars = '1234567890@,.+x'
        nums_found = False

        for char in ln:
            # some lines start with comments that we don't care about.
            # Attempt to remove them by scanning for the first number or '~'.
            if char.isnumeric() or char == '~':
                nums_found = True
            if nums_found and char in valid_chars:
                result += char

        return result.strip()


# Temporary Testing Area
if __name__ == '__main__':
    sql_utility = SQLUtility()

    sql_utility.import_sets_via_html('my_workouts.html', 'aliases.txt')
