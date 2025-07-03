"""
Contains utility functions for interacting with the SQLite database.
"""

import math
import os.path
import sqlite3
from datetime import date
from datetime import datetime
from typing import Dict

from common import hash_html, compress_html, decompress_html
from exercise_set import ExerciseSet

# Methods for importing exercise sets, implemented and not-yet-implemented.
HTML = 'HTML'
APPLE_NOTES = 'Apple Notes'

# Filepath for the user's SQLite file
SQLITE_FILE = "usr" + os.path.sep + "personal.db"

# Filepath for the user's exercise aliases file
ALIASES_FILE = "usr" + os.path.sep + "aliases.txt"

def create_tables():
    """
    Create tables in SQLite if they don't already exist. There are no primary
    keys because SQLite automatically creates the ROWID field for every item.
    """
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()
    # daily_sets
    # This represents all the sets a user has logged for a particular exercise on a particular date.
    # Ex: all bench press sets logged on 21 June 2025.
    # -> ('bb bench', '2025-06-21', '2x8@135, 2x6@145', 1)
    # date is stored in SQLite as TEXT (YYYY-MM-DD).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_sets(
            exercise TEXT,
            date TEXT,
            string TEXT,
            import_id INTEGER
        )
    """)
    # import
    # When the user imports exercise sets, the instance is recorded in this table.
    # file_hash is the content of the HTML file hashed. It's used for quick
    #   comparisons to avoid duplicate imports.
    # compressed_file_content is the content of the HTML compressed. It can be
    #   easily decompressed when the user wants to view the file content.
    # date_time is stored in SQLite as TEXT (YYYY-MM-DD HH:MM:SS).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import(
            date_time TEXT,
            file_hash TEXT,
            compressed_file_content BLOB,
            method TEXT
        )
    """)

    cur.close()
    con.close()


def get_imports():
    """
    Retrieve import items from SQLite, and return them as a list of tuples.
    This only returns the relevant fields needed to build the imports table.
    """
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()
    result = cur.execute("SELECT method, date_time, rowid FROM import")
    imports = result.fetchall()  # fetch list of tuples
    cur.close()
    con.close()
    return imports

def get_import_file_hashes_only():
    """
    Retrieve only file hashes of all import records in SQLite.
    :return: [('filehash1',), ('filehash2',)]
    """
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()
    result = cur.execute("SELECT file_hash FROM import")
    imports = result.fetchall()  # fetch list of tuples
    cur.close()
    con.close()
    return imports


def get_file_hash_and_content(import_row_id):
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()
    result = cur.execute(f"SELECT file_hash, compressed_file_content FROM import WHERE rowid = {import_row_id}")
    hash_and_content = result.fetchone()  # fetch 1 tuple
    cur.close()
    con.close()
    return hash_and_content


def delete_import(import_row_id):
    """
    Delete the given import and all daily_sets associated with the import.
    :return:
    """
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()
    cur.execute(f"DELETE FROM import WHERE rowid = {import_row_id}")
    cur.execute(f"DELETE FROM daily_sets WHERE import_id = {import_row_id}")
    con.commit()
    cur.close()
    con.close()


def get_exercise_sets_dict():
    """
    Retrieve daily_sets items from SQLite, convert them into ExerciseSet
    objects in Python, and build a dictionary that maps exercises to
    ExerciseSet objects.

    Example conversion from daily_sets to ExerciseSet objects (simplified):
    '2x8@135,6,5@145' -> 8@135, 8@135, 6@145, 5@145

    The exercise-sets dictionary maps
    exercise name (string) -> [individual sets associated with the exercise (ExerciseSet objects)]
    """
    print("\nBuilding Exercise-Sets Dictionary")
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()
    exercise_sets_dict = {}

    result = cur.execute("SELECT exercise, date, string FROM daily_sets")
    all_daily_sets_items = result.fetchall()
    for item in all_daily_sets_items:
        print(f'daily_sets item: {item}')
        # Convert daily_sets item in SQLite to ExerciseSet objects in Python
        individual_exercise_sets = get_exercise_sets_from_daily_sets(item)

        # Now add those ExerciseSet objects to the dict.
        if individual_exercise_sets:
            if len(individual_exercise_sets) > 6:
                print("WARNING, LOTS OF SETS FOUND")
            exercise = item[0]
            if exercise not in exercise_sets_dict.keys():
                exercise_sets_dict[exercise] = individual_exercise_sets
            else:
                exercise_sets_dict[exercise] += individual_exercise_sets

    cur.close()
    con.close()
    return exercise_sets_dict


def get_exercise_sets_from_daily_sets(daily_sets_item : tuple [str, str, str]):
    """
    Given a daily_sets item from SQLite, return a list of ExerciseSet objects.
    :return: all ExerciseSet objects that can be parsed from the daily_set item.
    """
    exercise, date_str, sets_str = daily_sets_item
    y, m, d = [int(p) for p in date_str.split('-')]
    date_of_sets = date(year=y, month=m, day=d)
    if sets_str.__contains__('@'):
        # These are sets for a typical weighted exercise
        return _get_weight_and_exercise_sets(exercise, sets_str, date_of_sets)
    else:
        # These are bodyweight sets
        return _get_exercise_sets(exercise, 0, sets_str, date_of_sets)


def _get_exercise_sets(exercise: str, weight: float, the_sets: str, date_of_sets: date):
    """
    This is the method that actually returns the ExerciseSet objects.

    :param exercise:                        example: 'bb bench'
    :param weight:                          example: 90.0
    :param the_sets:                        example: '2x10,~9'
    :param date_of_sets:                    example: 2025/05/27
    :return: list of ExerciseSet objects.   example: [(bb bench, 2025/05/27, 10@90.0), (bb bench, 2025/05/27, 10@90.0), (bb bench, 2025/05/27, ~9@90.0)]
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


def _get_weight_and_exercise_sets(exercise: str, sets_str: str, date_of_sets: date):
    """
    This function takes all the components of an SQL daily_sets item.
    It parses the string portion; delimits it by setsxreps + wt pairs; and for
    each pair, it calls _get_exercise_sets.

    :param exercise:      example: 'bb bench'
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
            exercise_sets += _get_exercise_sets(exercise, weight, the_sets, date_of_sets)
        except ValueError:
            print(f"SKIPPING MALFORMED LINE. Double check weight or syntax: {second_split[i]}@{second_split[i + 1]}")
            continue
    return exercise_sets


def get_alias_dict():
    """
    Return an alias dictionary from the given alias text file.

    The alias dictionary maps
    alias exercise name (string) -> common exercise name (string)

    If you want 'bb bench' to be the common exercise name, you could have the
    following mappings:
    - 'bench' -> 'bb bench'
    - 'bench press' -> 'bb bench'

    :return: alias dictionary
    """
    result = {}

    # TODO validate format of alias file?
    #  This could be done here, or when the user tries to save an invalid aliases file.

    with open(ALIASES_FILE, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            if line.startswith('#') or line == '':
                continue
            elif line.startswith('.'):
                curr_common_name = line[1:]
            else:
                result[line] = curr_common_name
    return result


def _parse_exercise(ln: str, alias_dict: Dict) -> str:
    """
    Parse exercise name from a line in an HTML file.

    :param ln: line in a workout file.   Ex: <li>Rear delt rows SS1 : 3x15 at 12.5<br></li>
    :param alias_dict: alias dictionary used to resolve aliases to common names
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
    # Going with singular names instead of plural for now.
    # TODO It would be nice if this were configurable and not hard-coded.
    result = result.replace(';', ',')
    result = result.replace('barbell', 'bb')
    result = result.replace('dumbbell', 'db')
    result = result.replace('ez bar', 'ezbar')
    result = result.replace('t bar', 'tbar')
    result = result.replace('hex bar', 'hexbar')
    result = result.replace('hexbar', 'hb')
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
        result = alias_dict[result]
    return result


def _sanitize_sets(ln: str) -> str:
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


def import_sets_via_html(html_filepath, existing_import_id=None):
    """
    This function reads an HTML file and inserts data into SQLite.

    :param html_filepath: HTML file to read
    :param existing_import_id: if not provided, an import record will be generated, and
        the sets will have an import ID that matches the new import.
        If provided, an import record will not be generated, and the sets will
        be tied to the provided import ID.
    :return:
    """
    alias_dict = get_alias_dict()

    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()

    daily_sets_list = []
    print(f"IMPORTING {html_filepath}")

    # Get hash and compressed content of HTML file.
    with open(html_filepath, 'r') as f:
        content = f.read()
    file_hash = hash_html(content)
    compressed_content = compress_html(content)

    # Parse the HTML file, and get a list of exercise sets to insert.
    with open(html_filepath, 'r') as f:
        parsing_exercises = False

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
                    exercise = _parse_exercise(line, alias_dict)

                    sets_str = _sanitize_sets(line[line.index(':'):])
                    if sets_str == "":
                        print("SKIPPING, NO SETS TO LOG.")
                    else:
                        daily_sets_item = (exercise, curr_date, sets_str)
                        print(f'  daily_sets found: {daily_sets_item}')
                        daily_sets_list.append(daily_sets_item)

    cur.execute("BEGIN TRANSACTION")

    # INSERT INTO SQLITE
    if existing_import_id is None:
        # Insert record into 'import' table
        now = datetime.today()
        now_str = f"{now.year}/{now.month}/{now.day} {now.hour}:{now.minute}:{now.second}"
        cur.execute(f"INSERT INTO import(date_time, file_hash, compressed_file_content, method) VALUES(?, ?, ?, ?)", (now_str, file_hash, compressed_content, HTML))

        # Insert records into 'daily_sets' table
        import_id = cur.lastrowid  # gets the most recent import id, TODO will this work in all cases?
        print(f"\ntime to insert: {daily_sets_list}")
        cur.executemany(f"INSERT INTO daily_sets(exercise, date, string, import_id) VALUES (?, ?, ?, {import_id})", daily_sets_list)
    else:
        # No new record will be inserted into 'import' table.
        # Insert records into 'daily_sets' table with the provided import_id
        print(f"\ntime to insert: {daily_sets_list}")
        cur.executemany(f"INSERT INTO daily_sets(exercise, date, string, import_id) VALUES (?, ?, ?, {existing_import_id})", daily_sets_list)

    con.commit()
    cur.close()
    con.close()


def update_daily_sets_to_alias():
    """Update the exercise of each daily_sets record to match the current alias file."""
    # We have to open and close a lot of connections because this function calls
    # a function that opens/closes a connection.
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()

    result = cur.execute("SELECT rowid FROM import")
    imports = result.fetchall()

    cur.close()
    con.close()

    # For each import:
    # - remember the ID
    # - delete daily_sets with this ID
    # - Decompress the HTML file associated with the import
    #    - also need to write the decompressed content to a new file so it can be opened.
    # - Parse the file and get daily_sets
    # - INSERT INTO daily_sets while maintaining the ID
    for imprt in imports:
        con = sqlite3.connect(SQLITE_FILE)
        cur = con.cursor()

        imprt_id = imprt[0]
        cur.execute(f"DELETE FROM daily_sets WHERE import_id = {imprt_id}")

        con.commit()
        cur.close()
        con.close()

        file_to_write = decompress_and_write_html(imprt_id)
        import_sets_via_html(html_filepath=file_to_write, existing_import_id=imprt_id)


def decompress_and_write_html(import_id: int) -> str:
    """
    Given an import rowid, decompress the file associated with the import,
    write the decompression to a new file, and return the path to that file.

    :param import_id: rowid of an 'import' record
    :return: path to decompressed HTML file
    """
    file_hash, file_compressed_content = get_file_hash_and_content(import_id)
    html_content = decompress_html(file_compressed_content)
    file_to_write = f'usr{os.path.sep}ben31w_{file_hash}.html'
    with open(file_to_write, 'w') as f:
        f.write(html_content)
    return file_to_write


# Temporary Testing Area
if __name__ == '__main__':
    create_tables()
    import_sets_via_html(f'html{os.path.sep}my_workouts.html')


    print("---# OF SETS LOGGED FOR EACH EXERCISE---")
    esd = get_exercise_sets_dict()

    sorted_dict = {key: val for key, val in
                   sorted(esd.items(), key=lambda ele: len(ele[1]), reverse=True)}
    for k, v in sorted_dict.items():
        print(f"{k}: {len(v)}")
