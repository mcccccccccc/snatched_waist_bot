from dataclasses import dataclass, field
from datetime import date
from typing import List, Tuple, Dict


@dataclass
class Profile:
    weight: int
    height: int
    age: int
    city: str
    activity: int
    calorie_goal: int = None
    logged_water: int = 0
    logged_calories: int = 0
    burned_calories: int = 0
    today: date = field(default_factory=date.today)
    trace_workout: List[Tuple[date, int]] = field(default_factory=list)
    trace_water: List[Tuple[date, int]] = field(default_factory=list)
    trace_food: List[Tuple[date, int]] = field(default_factory=list)


    def __str__(self):
        return f"Вес: {self.weight} кг\nРост: {self.height} см\nВозраст: {self.age} лет\nГород: {self.city}\nАктивность: {self.activity} минут в день\nЦель по калориям: {self.calorie_goal} ккал"

    def __repr__(self):
        return str(self)

    def to_dict(self) -> Dict:
        return self.__dict__