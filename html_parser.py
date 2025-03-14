import math

from exerciseset import ExerciseSet

# Set storing all unique exercises
exercises = set()

# dictionary storing exercise as key and number of workouts it's been in as value (TODO change to number of sets later)
exercise_set_dict = {}

def parse_exercise(ln: str) -> str:
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
    return result


def sanitize_sets(ln: str) -> str:
    """
    Given the portion of a workout line indicating the sets, strip comments and
    undesirable characters.
    :param ln: raw string of exercise sets.  Ex:  12 at 60, 2x9 at 70<br></li>
    :return: sanitized sets string.          Ex: 12@60,2x9@70
    """
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


def parse_sets(exercise: str, sets_str: str):
    """
    Given an exercise and sets string, get ExerciseSet objects.
    :param exercise:  example: 'bench'
    :param sets_str:  example: '10@65,~8@70,5+1@75,4,5@80,2x3@85,2x2,~1@90'
    :return: all ExerciseSet objects that can be parsed from the inputs.
    """
    print(f"Parsing sets, exercise='{exercise}' sets_str='{sets_str}'")
    if sets_str.__contains__('@'):
        return parse_weighted_sets(exercise, sets_str)
    else:
        return get_exercise_sets(exercise, 0, sets_str)  # parse body weight sets.


def parse_weighted_sets(exercise: str, sets_str: str):
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
        exercise_sets += get_exercise_sets(exercise, weight, the_sets)

    return exercise_sets


def get_exercise_sets(exercise: str, weight: float, the_sets: str):
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

        for i in range(num_sets):
            s = ExerciseSet(exercise=exercise, reps=num_reps, weight=weight, partial_reps=partial_reps)
            print(f"    {s}")
            exercise_sets.append(s)

    return exercise_sets


if __name__ == '__main__':
    print("---PARSING SETS FROM FILE---")
    with open('my_workouts.html', 'r') as f:
        parsing_exercises = False

        for line_num, line in enumerate(f.readlines(), start=1):
            line = line.lower()
            if line.__contains__("<body>"):
                parsing_exercises = True
            elif line.__contains__("</body>"):
                parsing_exercises = False

            # Lines with exercises are structured like this: "exercise : sets"
            if parsing_exercises and line.__contains__(':'):
                print(line_num, line.strip())
                exercise = parse_exercise(line)
                exercises.add(exercise)

                sets_str = sanitize_sets(line[line.index(':'):])
                if sets_str == "":
                    print("SKIPPING, NO SETS TO LOG.")
                else:
                    try:
                        ex_sets = parse_sets(exercise, sets_str)
                        if exercise not in exercise_set_dict:
                            exercise_set_dict[exercise] = len(ex_sets)
                        else:
                            exercise_set_dict[exercise] += len(ex_sets)
                    except ValueError:
                        print("ABORTING REST OF LINE BECAUSE OF VALUEERROR.")
                print()

    # for exercise in sorted(exercises):
    #     print(exercise)
    print(f"{len(exercises)} unique exercises found.")
    print()

    print("---# OF SETS LOGGED FOR EACH EXERCISE---")
    sorted_dict = {key:val for key, val in sorted(exercise_set_dict.items(), key = lambda ele: ele[1], reverse = True)}
    for k, v in sorted_dict.items():
        print(f"{k}: {v}")