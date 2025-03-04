# Set storing all unique exercises
exercises = set()

# dictionary storing exercise as key and number of workouts it's been in as value (change to number of sets later)
exercise_set_dict = {}

# dictionary storing file line as key and exercise as value (for debug use)
line_exercise_dict = {}

# For quick debug use. Can add problematic lines or edge cases for quick testing
test_lines = [
    "<body>",
    "<li>Pull ups (everything is taken :/ ): 14,10<br></li>",
    "<li>bb rows (o) (hyp) : 10,10,7+2 at 115<br></li>",
    "</body>"
]

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
    # TODO there are some malformed lines with bad characters (like semicolons)
    # that this doesn't work for.
    result = ""
    ln = ln.replace('at', '@')
    valid_chars = '1234567890@,.~+x;'

    for char in ln:
        if char in valid_chars:
            result += char
    return result


if __name__ == '__main__':
    with open('my_workouts.html', 'r') as f:
        parsing_exercises = False

        # for line in test_lines:
        for line_num, line in enumerate(f.readlines(), start=1):
            line = line.lower()
            if line.__contains__("<body>"):
                parsing_exercises = True
            elif line.__contains__("</body>"):
                parsing_exercises = False

            # Lines with exercises are structured like this: "exercise : sets"
            if parsing_exercises and line.__contains__(':'):
                exercise = parse_exercise(line)
                exercises.add(exercise)
                line_exercise_dict[line] = exercise

                sets = strip_line(line[line.index(':'):])
                print(f"{line_num}  {exercise}: {sets}")

                if exercise not in exercise_set_dict:
                    exercise_set_dict[exercise] = 1
                else:
                    exercise_set_dict[exercise] += 1

    # for exercise in sorted(exercises):
    #     print(exercise)
    print(f"{len(exercises)} unique exercises found.")

    # for line, exercise in line_exercise_dict.items():
    #     print(f"{line} : {exercise}")

    # sorted_dict = {key:val for key, val in sorted(exercise_set_dict.items(), key = lambda ele: ele[1], reverse = True)}
    # for k, v in sorted_dict.items():
    #     print(f"{k}: {v}")