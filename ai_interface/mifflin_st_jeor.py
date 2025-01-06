from enum import Enum
from database.food_database_model import (
    GoalValue, NutritionType, ActivityLevelValue
)


def calculate_nutrition(
    is_male: bool,
    age: int, weight_kg: float, height_cm: float,
    goal: GoalValue, activity_level: ActivityLevelValue,
    keto: bool
):
    if isinstance(goal, str):
        try:
            goal = GoalValue[goal]
        except KeyError:
            goal = GoalValue(goal)

    if isinstance(activity_level, str):
        try:
            activity_level = ActivityLevelValue[activity_level]
        except KeyError:
            activity_level = ActivityLevelValue(activity_level)

    if is_male:
        base_metabolic_rate = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        base_metabolic_rate = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity_multipliers = {
        ActivityLevelValue.LITTLE_TO_NO: 1.2,
        ActivityLevelValue.MODERATE_1_3_PER_WEEK: 1.375,
        ActivityLevelValue.HIGH_3_5_PER_WEEK: 1.55,
        ActivityLevelValue.VERY_HIGH_6_7_PER_WEEK: 1.725,
        ActivityLevelValue.HYPERACTIVE_2_HOURS_PER_DAY: 1.9,
    }

    adjusted_metabolic_rate = base_metabolic_rate * activity_multipliers[activity_level]

    calories_adjustment_for_goal = {
        GoalValue.LOSE_WEIGHT: 0.825,  # ~17.5% below TDEE (Total Daily Energy Expenditure)
        GoalValue.LOSE_WEIGHT_SLOWLY: 0.975,  # ~7.5% below TDEE
        GoalValue.MAINTAIN_WEIGHT: 1.0,  # TDEE
        GoalValue.GAIN_MUSCLE_SLOWLY: 1.075,  # ~7.5% surplus
        GoalValue.GAIN_MUSCLE: 1.175,  # ~17.5% surplus
    }

    nutrition_ratio_for_goal_keto = {
        GoalValue.LOSE_WEIGHT: {
            NutritionType.PROTEIN: 0.30,
            NutritionType.FAT: 0.65,
            NutritionType.CARBS: 0.05
        },
        GoalValue.LOSE_WEIGHT_SLOWLY: {
            NutritionType.PROTEIN: 0.25,
            NutritionType.FAT: 0.65,
            NutritionType.CARBS: 0.10
        },
        GoalValue.MAINTAIN_WEIGHT: {
            NutritionType.PROTEIN: 0.25,
            NutritionType.FAT: 0.70,
            NutritionType.CARBS: 0.05
        },
        GoalValue.GAIN_MUSCLE_SLOWLY: {
            NutritionType.PROTEIN: 0.30,
            NutritionType.FAT: 0.65,
            NutritionType.CARBS: 0.05
        },
        GoalValue.GAIN_MUSCLE: {
            NutritionType.PROTEIN: 0.35,
            NutritionType.FAT: 0.60,
            NutritionType.CARBS: 0.05
        },
    }

    nutrition_ratio_for_goal_balanced = {
        GoalValue.LOSE_WEIGHT: {
            NutritionType.PROTEIN: 0.30,
            NutritionType.FAT: 0.25,
            NutritionType.CARBS: 0.45,
        },
        GoalValue.LOSE_WEIGHT_SLOWLY: {
            NutritionType.PROTEIN: 0.25,
            NutritionType.FAT: 0.25,
            NutritionType.CARBS: 0.50,
        },
        GoalValue.MAINTAIN_WEIGHT: {
            NutritionType.PROTEIN: 0.25,
            NutritionType.FAT: 0.25,
            NutritionType.CARBS: 0.50,
        },
        GoalValue.GAIN_MUSCLE_SLOWLY: {
            NutritionType.PROTEIN: 0.30,
            NutritionType.FAT: 0.30,
            NutritionType.CARBS: 0.40,
        },
        GoalValue.GAIN_MUSCLE: {
            NutritionType.PROTEIN: 0.35,
            NutritionType.FAT: 0.25,
            NutritionType.CARBS: 0.40,
        },
    }

    if keto:
        nutrition_ratio_for_goal = nutrition_ratio_for_goal_keto
    else:
        nutrition_ratio_for_goal = nutrition_ratio_for_goal_balanced

    calories_multiplier = calories_adjustment_for_goal[goal]
    nutrition_ratio = nutrition_ratio_for_goal[goal]

    calories_target = adjusted_metabolic_rate * calories_multiplier

    target = {NutritionType.CALORIES: calories_target}
    nutrition_keys = [NutritionType.PROTEIN, NutritionType.FAT, NutritionType.CARBS]
    for n in nutrition_keys:
        target[n] = calories_target * nutrition_ratio[n] / n.calories()

    return target
