from datetime import date, datetime, timedelta

class DailySets:
    """Represents a daily_sets item in the database."""
    def __init__(self, daily_sets_tuple: tuple[str, str, str, str]):
        self.exercise: str = daily_sets_tuple[0]
        self.date: date = datetime.strptime(daily_sets_tuple[1], "%Y-%m-%d").date()
        self.sets_string: str  = daily_sets_tuple[2]
        self.comments: str = daily_sets_tuple[3]

    def __str__(self) -> str:
        return f"{self.date}, {self.exercise}, {self.sets_string} ({self.comments})"


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

    def get_start_end_dates(self) -> tuple[date, date]:
        self.daily_sets_list.sort(key=lambda ds: ds.date)
        start: date = self.daily_sets_list[0].date
        end: date = self.daily_sets_list[-1].date
        return start, end

    def get_length_string(self) -> str:
        """
        Return a string representing the length of the exercise arc.
        It's approximate.
        """
        start, end = self.get_start_end_dates()
        td: timedelta = end - start
        approx_years: int = td.days // 365
        approx_months: int = td.days % 365 // 30

        if approx_years == 0:
            if approx_months == 0:
                return "<1 month"
            return f"{approx_months} months"
        else:
            if approx_months == 0:
                return f"{approx_years} years"
            return f"{approx_years} years, {approx_months} months"
