from datetime import date


class ExerciseSet:
    """A set of an exercise."""
    def __init__(self, exercise: str, reps: int, weight: float, partial_reps: bool, date: date):
        self.exercise = exercise
        self.reps = reps
        self.weight = weight
        self.partial_reps = partial_reps
        self.date = date


    def __str__(self):
        """
        Return a string representation of this set.
        :return: exercise: reps@WT (date)
        """
        if self.weight == 0:
            return f"{self.exercise}: {self.reps} ({self.date})"
        return f"{self.exercise}: {self.reps}@{self.weight}  ({self.date})"


    def simple_str(self):
        """
        Return a simple string representation of this set
        :return: reps@WT
        """
        return f"{self.reps}@{self.weight}" if self.weight != 0 else f"{self.reps}"
