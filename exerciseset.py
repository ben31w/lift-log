class ExerciseSet:
    """A set of an exercise."""
    def __init__(self, exercise: str, reps: int, weight: float, partial_reps: bool):
        self.exercise = exercise
        self.reps = reps
        self.weight = weight
        self.partial_reps = partial_reps


    def __str__(self):
        if self.weight == 0:
            return f"{self.exercise}: {self.reps}"
        return f"{self.exercise}: {self.reps}@{self.weight}"
