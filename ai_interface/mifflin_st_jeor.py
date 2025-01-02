class Meal:
    def __init__(
        self,
        calories,
        protein,
        fat,
        carb
    ):
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carb = carb


def calories_from_macros(
    fat, carb, protein
):
    return protein * 4.0 + carb * 4.0 + fat * 9.0


def calculate_nutrition(
    is_male: bool,
    age: int,
    weight_kg: float,
    height_cm: float,
    goal: str,
    activity_level: str = 'sedentary'
):
    if is_male:
        base_metabolic_rate = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        base_metabolic_rate = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity_multipliers = {
        "sedentary": 1.2,
        "lightly active": 1.375,
        "moderately active": 1.55,
        "very active": 1.725,
        "extremely active": 1.9
    }

    adjusted_metabolic_rate = base_metabolic_rate * activity_multipliers[activity_level]

    goals_data = {
        "lose weight": {
            "cal_adjust": -0.20,
            "protein_ratio": 0.40,
            "fat_ratio": 0.30,
            "carb_ratio": 0.30,
        },
        "lose weight slowly": {
            "cal_adjust": -0.10,
            "protein_ratio": 0.35,
            "fat_ratio": 0.25,
            "carb_ratio": 0.40,
        },
        "maintain weight": {
            "cal_adjust": 0.00,
            "protein_ratio": 0.30,
            "fat_ratio": 0.25,
            "carb_ratio": 0.45,
        },
        "gain muscles slowly": {
            "cal_adjust": 0.10,
            "protein_ratio": 0.30,
            "fat_ratio": 0.25,
            "carb_ratio": 0.45,
        },
        "gain muscles": {
            "cal_adjust": 0.20,
            "protein_ratio": 0.25,
            "fat_ratio": 0.25,
            "carb_ratio": 0.50,
        },
    }

    cal_adjust = goals_data[goal]["cal_adjust"]
    protein_ratio = goals_data[goal]["protein_ratio"]
    fat_ratio = goals_data[goal]["fat_ratio"]
    carb_ratio = goals_data[goal]["carb_ratio"]

    daily_calories = adjusted_metabolic_rate * (1 + cal_adjust)

    #    1g protein = 4 kcal, 1g carbs = 4 kcal, 1g fat = 9 kcal
    protein_g = (daily_calories * protein_ratio) / 4.0
    fat_g = (daily_calories * fat_ratio) / 9.0
    carbs_g = (daily_calories * carb_ratio) / 4.0

    return {
        "daily_calories": round(daily_calories, 1),
        "protein_g": round(protein_g, 1),
        "fat_g": round(fat_g, 1),
        "carbs_g": round(carbs_g, 1),
    }
