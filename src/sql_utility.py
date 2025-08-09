"""
Contains utility functions for interacting with the SQLite database.
"""
import logging
import math
import os.path
import sqlite3
from datetime import date
from datetime import datetime
from tkinter import END, Text
from typing import Dict

from common import hash_html, compress_html, decompress_html, print_to_text_widget
from exercise_set import ExerciseSet

logger = logging.getLogger(__name__)

# Filepath for the user's SQLite file
SQLITE_FILE = "usr" + os.path.sep + "personal.db"

# Filepath for the user's exercise aliases file
ALIASES_FILE = "usr" + os.path.sep + "aliases.txt"

# These are the tag names used by the Import Status Msg Area.
# They mirror the built-in logging level names.
# The constants built into Python logging are actually integers.
# We care about the string representations because those are the tag names.
# TODO there are probably cleaner ways of managing this.
DEBUG = 'DEBUG'
INFO = 'INFO'
WARNING = 'WARNING'
ERROR = 'ERROR'
CRITICAL = 'CRITICAL'

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
    #     -> ('bb bench', '2025-06-21', '2x8@135, 2x6@145', 1)
    # date is stored in SQLite as TEXT (YYYY-MM-DD).
    # is_valid is a boolean (0/1), but SQLite stores booleans as INTEGER
    # TODO comments and is_valid aren't being set or used yet
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_sets(
            exercise TEXT,
            date TEXT,
            sets_string TEXT,
            comments TEXT,
            is_valid INTEGER,
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
            name TEXT
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
    result = cur.execute("SELECT name, date_time, rowid FROM import")
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
    logger.info("Building Exercise-Sets Dictionary")
    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()
    exercise_sets_dict = {}

    result = cur.execute("SELECT exercise, date, sets_string FROM daily_sets WHERE is_valid = 1")
    all_daily_sets_items = result.fetchall()
    for item in all_daily_sets_items:
        logger.debug(f'daily_sets item: {item}')
        # Convert daily_sets item in SQLite to ExerciseSet objects in Python
        individual_exercise_sets = get_exercise_sets_from_daily_sets(item)

        # Now add those ExerciseSet objects to the dict.
        if individual_exercise_sets:
            if len(individual_exercise_sets) > 6:
                logger.warning(f"More than 6 sets detected for {item}")
                logger.warning("  These sets will still be added.")
            exercise = item[0]
            if exercise not in exercise_sets_dict.keys():
                exercise_sets_dict[exercise] = individual_exercise_sets
            else:
                exercise_sets_dict[exercise] += individual_exercise_sets

    cur.close()
    con.close()
    logger.info("Done building Exercise-Sets Dictionary")
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
        reps = reps.replace('~', '')

        # Account for '+' (disjoint reps).  ex: 5+1 => 6
        # Also, account for half reps indicated by decimal point. ex: 4.5 => 4
        try:
            num_reps = sum([math.trunc(float(r)) for r in reps.split('+')])  # "5+1" = 6
        except ValueError:
            logger.warning(f"Failed to parse num_reps. {date_of_sets}, {exercise}: {the_set}")
            continue

        if num_reps > 100:
            logger.warning(f"Suspiciously high number of reps. {date_of_sets}, {exercise}: {num_reps} @ {weight}")
            logger.warning("  This set won't be added.")
            break

        for i in range(num_sets):
            s = ExerciseSet(exercise=exercise, reps=num_reps, weight=weight, partial_reps=partial_reps, date=date_of_sets)
            logger.debug(f"    {s}")
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
    sets_str_split = _split_sets_string(sets_str)

    for i in range(0, len(sets_str_split), 2):
        the_sets = sets_str_split[i]  # '10' '~8' ... '2x2,~1'
        try:
            weight = float(sets_str_split[i + 1])  # 65 70 ... 90
            logger.debug(f"  {the_sets}@{weight}")
            exercise_sets += _get_exercise_sets(exercise, weight, the_sets, date_of_sets)
        except ValueError:
            logger.warning(f"A weight couldn't be parsed from this set string: {date_of_sets}, {exercise}: {sets_str}")
            logger.warning("  Sets at the invalid weight won't be added.")
            continue
    return exercise_sets


def _split_sets_string(sets_str: str) -> list[str]:
    """
    Split sets_str into a list with format [setsxreps, wt, setsxreps, wt, ... ].
    TODO it might be nice to use tuples.
    :param sets_str: sets_str of a daily_sets item
    :return: list of [setsxreps, wt, setsxreps, wt, ... ]
    """
    # input:               '10@65,~8@70,5+1@75,4,5@80,2x3@85,2x2,~1@90'
    # first_split format:  ['10', '65', '~8', '70,5+1', '75,4,5', '80,2x3', '85,2x2,~1', '90']
    # second_split format: ['10', '65', '~8', '70', '5+1', '75', '4,5', '80', '2x3', '85', '2x2,~1', '90']
    first_split = sets_str.split("@")
    second_split = [first_split[0]]
    # don't split by comma for the first item. The first item always indicates reps (not weight)
    for part in first_split[1:]:
        subparts = part.split(',', maxsplit=1)
        for subpart in subparts:
            second_split.append(subpart)
    return second_split


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

    :param ln: part of HTML line containing exercise (part before colon).
               Ex: <li>Rear delt rows SS1
    :param alias_dict: alias dictionary used to resolve aliases to common names
    :return:  exercise name in the line. Ex: 'rear delt row'
    """
    # First characters in the line might be "<li>" or "<div>", which can be ignored.
    # If these aren't the first characters, this works regardless.
    result = ln[ln.index('>') + 1:]

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


def _sanitize_sets(ln: str) -> (str, str):
    """
    Given the portion of a workout line indicating the sets, strip comments and
    undesirable characters.

    :param ln: raw string of exercise sets.  Ex:  12 at 60, 2x9 at 70<br></li>
    :return: sanitized sets string.          Ex: 12@60,2x9@70
    """
    # Skip drop sets (for now?)
    if ln.__contains__('drop'):
        return "", ""

    # Remove HTML tags. We assume that the opening HTML tag should not make it
    # to this function call. So we are stripping <br>, </div>, </li>, etc.
    idx_tag = ln.index('<')
    if idx_tag != -1:
        ln = ln[:idx_tag]

    # First, attempt to retrieve comments.
    # Split by commas, and check each part for commas:
    # (1) If any part starts with a letter, it's a comment.
    # (2) Within each part, if there are characters that don't fit our valid
    #     set syntax, then they indicate the start of a comment.
    ln = ln.replace(';', ',')
    ln = ln.replace('at', '@')
    parts = ln.split(',')
    sanitized_parts = []
    start_of_set_chars = '123456789~'
    set_chars = start_of_set_chars + '0@,.+x '
    comments = ""
    for part in parts:
        part = part.strip()
        if len(part) == 0:
            continue
        elif part[0] not in start_of_set_chars:  # (1)
            comments += f"{part} "
            continue

        for i in range(len(part)):  # (2)
            if part[i] not in set_chars:
                part = part[:i]  # set string
                comment = part[i:]
                comments += f"{comment} "
                break
        sanitized_parts.append(part)

    result = ",".join(sanitized_parts)

    # Some extra sanitization
    result = result.replace(' ', '')  # temporary, maybe
    result = result.replace(',,', ',')
    result = result.replace(',@', '@')
    result = result.replace('@,', '@')
    result = result.replace('+@', '@')

    return result.strip(), comments.strip()


def import_sets_via_html(html_filepath:str,
                         existing_import_id:int=None,
                         text_widget:Text=None,
                         clear_text_widget:bool=True,
                         method:str='HTML'):
    """
    This function reads an HTML file and inserts data into SQLite.

    Assumption:
    the HTML is formatted so that headings, paragraphs, list items, etc. are on their own line.
    not allowed: '<h1>My Workouts</h1><h2>8/6/2025</h2>'

    :param html_filepath: HTML file to read
    :param existing_import_id: if not provided, an import record will be generated, and
        the sets will have an import ID that matches the new import.
        If provided, an import record will not be generated, and the sets will
        be tied to the provided import ID.
    :param text_widget: log messages can optionally be logged to a tkinter
        Text widget too.
    :param clear_text_widget: can specify whether to clear the content of the text
        widget before importing
    :param method: The method for this import (HTML, Apple Notes), which becomes part of the
        name that we store in SQLite and display in the GUI.
    :return:
    """
    alias_dict = get_alias_dict()

    con = sqlite3.connect(SQLITE_FILE)
    cur = con.cursor()

    daily_sets_list = []

    if text_widget is not None:
        text_widget.configure(state='normal')
        if clear_text_widget:
            text_widget.delete("1.0", END)

    _log_import_msg(f"Importing {html_filepath}", text_widget)

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
                        _log_import_msg(f"Current date: {curr_date}", text_widget, DEBUG)
                    except ValueError:
                        # TODO if we fail to parse a date from the h2 tag, should
                        #  the sets that follow be imported at all?
                        #  Right now, we are continuing to import them, with possibly the wrong date.
                        _log_import_msg(f"Failed to parse date from line {line_num}: '{line}'", text_widget, WARNING)
                        _log_import_msg(f"^got date_part='{date_part}'", text_widget, DEBUG)
                        _log_import_msg(f"The last valid date will be used ({curr_date})", text_widget, WARNING)

                # Lines with exercises are structured like this: "exercise : sets"
                #   more specifically:
                #     [<li>] exercise: {( {SetsxReps} | {Reps} )@weight}[, comments] [</li>]
                #     Ex: <li>Rear delt rows SS1 : 3x15 at 12.5<br></li>
                elif line.__contains__(':'):
                    _log_import_msg(f"(line {line_num}) {line}", text_widget, DEBUG)
                    exercise_part, sets_str_part = line.split(':', maxsplit=1)
                    exercise = _parse_exercise(exercise_part, alias_dict)
                    try:
                        sets_str, comments = _sanitize_sets(sets_str_part)
                    except ValueError:
                        _log_import_msg(f"Error parsing this line. {line_num}: '{line}'", text_widget, ERROR)

                    if sets_str == "":
                        _log_import_msg(f"Skipping. No sets were found on line {line_num}: '{line}'", text_widget, WARNING)
                    else:
                        is_valid = _is_sets_string_valid(sets_str)
                        if not is_valid:
                            _log_import_msg(f"Invalid sets string found on line {line_num}: '{line}'  |  sets_str: {sets_str}", text_widget, WARNING)

                        daily_sets_item = (exercise, curr_date, sets_str, is_valid, comments)
                        _log_import_msg(f'  daily_sets found: {daily_sets_item}', text_widget, DEBUG)
                        daily_sets_list.append(daily_sets_item)

    cur.execute("BEGIN TRANSACTION")

    # INSERT INTO SQLITE
    if existing_import_id is None:
        # Insert record into 'import' table
        cur.execute(f"INSERT INTO import(date_time, file_hash, compressed_file_content) VALUES(DATETIME(), ?, ?)", (file_hash, compressed_content))

        # Insert records into 'daily_sets' table
        import_id = cur.lastrowid  # gets the most recent import id, TODO will this work in all cases?
        cur.executemany(f"INSERT INTO daily_sets(exercise, date, sets_string, is_valid, comments, import_id) VALUES (?, ?, ?, ?, ?, {import_id})", daily_sets_list)

        # Now, update the 'name' field of our new 'import' record.
        min_date = cur.execute(f"SELECT MIN(date) FROM daily_sets WHERE import_id = {import_id}").fetchone()[0]
        max_date = cur.execute(f"SELECT MAX(date) FROM daily_sets WHERE import_id = {import_id}").fetchone()[0]
        name = f"{method}, {min_date} to {max_date}"
        cur.execute(f"UPDATE import SET name = '{name}' WHERE ROWID = {import_id}")
    else:
        # No new record will be inserted into 'import' table.
        # Insert records into 'daily_sets' table with the provided import_id
        cur.executemany(f"INSERT INTO daily_sets(exercise, date, sets_string, is_valid, comments, import_id) VALUES (?, ?, ?, ?, ?, {existing_import_id})", daily_sets_list)

    _log_import_msg("Done importing.", text_widget)
    if text_widget is not None:
        text_widget.configure(state='disabled')

    con.commit()
    cur.close()
    con.close()

def _is_sets_string_valid(sets_str : str) -> bool:
    """
    Return True if the given sets string has valid syntax.

    Current checks:
    - sets strings without '@' are unweighted sets, which we assume are valid
    - sets string with '@' are weighted. We check:
      (1) does the sets string contain an equal amount of setsxreps and weights?
      (2) can the last weight (i.e., element after last @) be converted to a float?

    This is a very crude check that may falsely label some sets strings as valid.
    The logic that reads SQLite and converts daily_sets items to
    ExerciseSets objects performs additional checks for now.
    """
    if '@' not in sets_str:
        return True

    sets_str_split = _split_sets_string(sets_str)

    if len(sets_str_split) % 2 != 0:  # (1)
        return False

    last_wt = sets_str_split[-1]  # (2)
    try:
        float(last_wt)
    except ValueError:
        return False
    return True


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


def _log_import_msg(msg, text_widget, level="INFO"):
    """
    Logging helper method for import_sets_via_html.
    Logs the given msg to the logger and the text_widget.
    :param msg:    message to log
    :param text_widget: tkinter Text widget to send msg to
    :param level:  logging level for msg
    :return:
    """
    # 10 = DEBUG
    # 20 = INFO
    # 30 = WARNING
    # 40 = ERROR
    # 50 = CRITICAL
    logger_level = logger.getEffectiveLevel()
    match level:
        case "DEBUG":
            logger.debug(msg)
            if logger_level <= 10:
                print_to_text_widget(msg, text_widget, level)
        case "INFO":
            logger.info(msg)
            if logger_level <= 20:
                print_to_text_widget(msg, text_widget, level)
        case "WARNING":
            logger.warning(msg)
            if logger_level <= 30:
                print_to_text_widget(msg, text_widget, level)
        case "ERROR":
            logger.error(msg)
            if logger_level <= 40:
                print_to_text_widget(msg, text_widget, level)
        case "CRITICAL":
            logger.critical(msg)
            print_to_text_widget(msg, text_widget, level)

    # match level:
    #     case logging.DEBUG:
    #         print()
    #
    # if logger_level <= level:
    #     print_to_text_widget(msg, text_widget, level)

