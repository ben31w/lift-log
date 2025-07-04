"""
Python class representing a single exercise set.

This is different from the SQLite daily_sets item, which represents all
exercise sets performed on one day for a particular exercise.

One daily_sets record can be converted to 1+ ExerciseSet objects.
'2x10@135, 8,7@145' -> 10@135, 10@135, 8@145, 7@145

This class is used to plots the sets.
"""
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
        return f"{self.exercise}: {self.reps}@{self.truncate_weight()}  ({self.date})"


    def simple_str(self):
        """
        Return a simple string representation of this set
        :return: reps@WT
        """
        return f"{self.reps}@{self.truncate_weight()}" if self.weight != 0 else f"{self.reps}"


    def truncate_weight(self):
        """
        If this set's weight is an integer, return it as an integer.
        Otherwise, return the weight as is (as a float).
        """
        if self.weight == int(self.weight):
            return int(self.weight)
        else:
            return self.weight
