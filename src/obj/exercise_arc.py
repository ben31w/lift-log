from datetime import datetime

class DailySets:
    """Represents a daily_sets item in the database."""
    def __init__(self, daily_sets_tuple: tuple[str, str, str, str]):
        self.exercise = daily_sets_tuple[0]
        self.date = datetime.strptime(daily_sets_tuple[1], "%Y-%m-%d").date()
        self.sets_string = daily_sets_tuple[2]
        self.comments = daily_sets_tuple[3]


class ExerciseArc:
    """
    An exercise arc represents a dedicated training period for one exercise.
    It consists of an ordered list of DailySets items.
    """
    def __init__(self, initial_items=None):
        if initial_items is None:
            initial_items = []
        self.daily_sets_list: list[DailySets] = initial_items

    def __len__(self):
        return len(self.daily_sets_list)

    def add_daily_sets_obj(self, daily_sets_obj: DailySets) -> None:
        self.daily_sets_list.append(daily_sets_obj)

    def add_daily_sets_tuple(self, daily_sets_tuple: tuple[str, str, str, str]) -> None:
        daily_sets_obj = DailySets(daily_sets_tuple)
        self.daily_sets_list.append(daily_sets_obj)
