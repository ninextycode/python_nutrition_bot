from pydantic import BaseModel


class MealData(BaseModel):
    description: str
    proteins: int
    fats: int
    carbohydrates: int
    energy: int
    total_weight: int
    success_flag: bool
    error_message: str


class ImageObject:
    def __init__(self, byte_data, extension):
        self.byte_data = byte_data
        self.extension = extension


class OpenaiMealChat:
    def __init__(self):
        pass

    def get_meal_description(self, description=None, image_object=None):
        pass

    def update_meal_description(self, update_request):
        pass

