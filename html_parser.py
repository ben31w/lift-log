# Set storing all unique exercises
from functools import partial

from exerciseset import ExerciseSet

exercises = set()

# dictionary storing exercise as key and number of workouts it's been in as value (change to number of sets later)
exercise_set_dict = {}

def parse_exercise(ln: str) -> str:
    """
    Parse exercise from a line.
    :param ln: line in a workout file
    :return:  exercise name in the line
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
    # Probably want a better way of aliasing exercises though.
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


def strip_line(ln: str) -> str:
    """
    Strip comments and undesirable characters from a line of exercise sets.
    :param ln: line to strip
    :return: stripped line
    """
    result = ""
    ln = ln.replace('at', '@')
    ln = ln.replace(';', ',')
    valid_chars = '1234567890@,.+x'

    for char in ln:
        if char in valid_chars:
            result += char
    return result


def parse_sets(exercise: str, sets_str: str):
    """
    Given an exercise and sets string, create ExerciseSet objects.
    :param exercise:  example: 'bench'
    :param sets_str:  example: '10@65,~8@70,5+1@75,4,5@80,2x3@85,2x2,~1@90'
    :return:
    """
    print(f"Parsing sets from ({exercise}) {sets_str}")

    first_split = sets_str.split("@")  # '10', '65', '~8', '70,5+1', '75,4,5', '80,2x3', '85,2x2,~1', '90'
    second_split = []  # '10', '65', '~8', '70', '5+1', '75', '4,5', '80', '2x3', '85', '2x2,~1', '90'
    for part in first_split:
        subparts = part.split(',', maxsplit=1)
        for subpart in subparts:
            second_split.append(subpart)

    for i in range(0, len(second_split), 2):
        the_sets = second_split[i]  # '10' '~8' ... '2x2,~1'
        weight = float(second_split[i+1])  # 65 70 ... 90
        print(f"  {the_sets}@{weight}")

        # To get all the sets associated with this weight, first split by comma.
        for the_set in the_sets.split(","):
            # Now check for 'x', which indicates multiple sets with the same reps
            if the_set.__contains__('x'):  # ex: '2x2'
                num_sets, num_reps = the_set.split('x')
            else:  # ex: '10'
                num_sets = 1
                num_reps = the_set

            # Lastly, need to account for '~' (partial reps) and '+' (disjoint reps)
            partial_reps = num_reps.__contains__('~')
            num_reps.replace('~', '')

            actual_num_reps = sum([int(r) for r in num_reps.split('+')])  # "5+1" = 6

            for i in range(int(num_sets)):
                s = ExerciseSet(exercise=exercise, reps=actual_num_reps, weight=weight, partial_reps=partial_reps)
                print(f"    {s}")


if __name__ == '__main__':
    with open('my_workouts_lite.html', 'r') as f:
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

                sets_str = strip_line(line[line.index(':'):])
                parse_sets(exercise, sets_str)
                print()

                if exercise not in exercise_set_dict:
                    exercise_set_dict[exercise] = 1
                else:
                    exercise_set_dict[exercise] += 1

    # for exercise in sorted(exercises):
    #     print(exercise)
    print(f"{len(exercises)} unique exercises found.")

    # sorted_dict = {key:val for key, val in sorted(exercise_set_dict.items(), key = lambda ele: ele[1], reverse = True)}
    # for k, v in sorted_dict.items():
    #     print(f"{k}: {v}")