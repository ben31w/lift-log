from datetime import date
import math
from typing import Dict

from exercise_set import ExerciseSet


class HtmlParser:
    """
    This class takes an HTML file containing exercise sets and tracks
    information about the sets.
    """
    
    def __init__(self, html_filepath : str, alias_filepath : str=None):
        # Set storing all unique exercises
        self.exercises = set()
        
        # key = exercise
        # value = list of ExerciseSet objects associated with the exercise
        self.exercise_set_dict: Dict[str, list[ExerciseSet]] = {}

        # Some variables used when creating the alias dict
        self.next_exercise_is_common = False
        self.curr_common_name = ""

        # key = exercise name
        # value = an equivalent common exercise name that is equivalent to the key
        self.alias_dict: Dict[str, str] = {}
        if alias_filepath is not None:
            self.parse_alias_file(alias_filepath)

        self.parse_html_file(html_filepath)

    def parse_alias_file(self, alias_filepath : str):
        """Parse alias txt file, and populate the alias dictionary."""
        with open(alias_filepath, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line.startswith('#') or line == '':
                    continue
                elif line.startswith('.'):
                    self.next_exercise_is_common = True
                    if len(line) > 1:
                        self.add_exercise_to_alias_dict(exercise=line[1:])
                else:
                    self.add_exercise_to_alias_dict(exercise=line)

    def add_exercise_to_alias_dict(self, exercise : str):
        # If this exercise is the common name, set some variables, but don't add anything to the dict.
        if self.next_exercise_is_common:
            self.curr_common_name = exercise
            self.next_exercise_is_common = False
            return
        self.alias_dict[exercise] = self.curr_common_name

    def parse_html_file(self, html_file_path : str):
        print("---PARSING SETS FROM FILE---")
        with open(html_file_path, 'r') as f:
            parsing_exercises = False
            curr_date = date.today()

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
                            date_part = line[len("<h2>") : len(line) - len("</h2>")].split(" ")[0]
                            month, day, year = [int(item) for item in date_part.split("/", 3)]
                            if year < 2000:  # Sometimes year is formatted with only two digits.
                                year += 2000
                            curr_date = date(year, month, day)
                            print(f"CURR DATE: {curr_date}")
                        except ValueError:
                            print(
                                f"FAILED TO PARSE DATE FROM {line_num}. line='{line}'  date_part='{date_part}'")

                    # Lines with exercises are structured like this: "exercise : sets"
                    elif line.__contains__(':'):
                        print(line_num, line)
                        exercise = self.parse_exercise(line)
                        self.exercises.add(exercise)

                        sets_str = self.sanitize_sets(line[line.index(':'):])
                        if sets_str == "":
                            print("SKIPPING, NO SETS TO LOG.")
                        else:
                            try:
                                ex_sets = self.parse_sets(exercise, sets_str, curr_date)
                                if len(ex_sets) > 6:
                                    print("WARNING, LOTS OF SETS FOUND")
                                if exercise not in self.exercise_set_dict:
                                    self.exercise_set_dict[exercise] = ex_sets
                                else:
                                    self.exercise_set_dict[exercise] += ex_sets
                            except ValueError:
                                print("ABORTING REST OF LINE BECAUSE OF VALUEERROR.")
                        print()

        print(f"{len(self.exercises)} unique exercises found.")
        print()

        print("---# OF SETS LOGGED FOR EACH EXERCISE---")
        sorted_dict = {key: val for key, val in
                       sorted(self.exercise_set_dict.items(), key=lambda ele: len(ele[1]), reverse=True)}
        for k, v in sorted_dict.items():
            print(f"{k}: {len(v)}")

    def parse_exercise(self, ln: str) -> str:
        """
        Parse exercise from a line.
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
        if result in self.alias_dict.keys():
            result = self.alias_dict[result]

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


    def parse_sets(self, exercise: str, sets_str: str, date_of_sets: date):
        """
        Given an exercise and sets string, get ExerciseSet objects.
        :param exercise:  example: 'bench'
        :param sets_str:  example: '10@65,~8@70,5+1@75,4,5@80,2x3@85,2x2,~1@90'
        :param date_of_sets:  the date these sets were performed (as a Python date object)
        :return: all ExerciseSet objects that can be parsed from the inputs.
        """
        print(f"Parsing sets, exercise='{exercise}' sets_str='{sets_str}'")
        if sets_str.__contains__('@'):
            return self.parse_weighted_sets(exercise, sets_str, date_of_sets)
        else:
            return self.get_exercise_sets(exercise, 0, sets_str, date_of_sets)  # parse body weight sets.


    def parse_weighted_sets(self, exercise: str, sets_str: str, date_of_sets: date):
        """
        Given an exercise and sets string, get ExerciseSet objects.
        :param exercise:  example: 'bench'
        :param sets_str:  example: '10@65,~8@70,5+1@75,4,5@80,2x3@85,2x2,~1@90'
        :return:  all ExerciseSet objects that can be parsed from the inputs.
        """
        exercise_sets = []

        # Split sets_str into a list with format [setsxreps, wt, setsxreps, wt, ... ]  # TODO it might be nice to use tuples
        first_split = sets_str.split("@")  # '10', '65', '~8', '70,5+1', '75,4,5', '80,2x3', '85,2x2,~1', '90'
        second_split = [first_split[0]]  # '10', '65', '~8', '70', '5+1', '75', '4,5', '80', '2x3', '85', '2x2,~1', '90'
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
        :param exercise: 'bench'
        :param weight:   90.0
        :param the_sets: '2x2,~1'
        :return: list of ExerciseSet objects
        """
        exercise_sets = []

        for the_set in the_sets.split(","):
            # Check for 'x', which indicates multiple sets with the same reps
            if the_set.__contains__('x'):  # ex: '2x2'
                setsxreps = the_set.split('x')
                num_sets = int(setsxreps[0])
                reps = setsxreps[1]
            else:  # ex: '~1'
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


if __name__ == '__main__':
    html_parser = HtmlParser('my_workouts.html', 'aliases.txt')
