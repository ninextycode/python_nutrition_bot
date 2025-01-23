from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import threading
import datetime
import decimal
import pytz
from database import common_sql
from enum import Enum


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


class Base(DeclarativeBase):
    metadata = sa.MetaData(naming_convention=naming_convention)

    def __repr__(self):
        data = {col.name: getattr(self, col.name, None) for col in self.__table__.columns}
        return f"{self.__class__.__name__}({', '.join(f'{k}={v!r}' for k, v in data.items())})"


class Gender(Base):
    __tablename__ = "genders"
    __table_args__ = (
        sa.UniqueConstraint("gender"),
    )

    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False,
        autoincrement=True
    )
    gender: Mapped[str] = mapped_column(mysql.VARCHAR(50), nullable=False)
    users: Mapped[List["User"]] = relationship("User", back_populates="gender_obj")


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        sa.UniqueConstraint("goal"),
    )

    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False,
        autoincrement=True
    )
    goal: Mapped[str] = mapped_column(mysql.VARCHAR(200), nullable=False)
    users: Mapped[List["User"]] = relationship("User", back_populates="goal_obj")


class ActivityLevel(Base):
    __tablename__ = "activity_levels"
    __table_args__ = (
        sa.UniqueConstraint("name"),
    )

    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(mysql.VARCHAR(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(mysql.VARCHAR(5000), nullable=False)
    users: Mapped[List["User"]] = relationship("User", back_populates="activity_level_obj")


class TimeZone(Base):
    __tablename__ = "timezones"
    __table_args__ = (
        sa.UniqueConstraint("timezone"),
    )
    timezones_update_lock = threading.Lock()
    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False,
        autoincrement=True
    )
    timezone: Mapped[str] = mapped_column(mysql.VARCHAR(200), nullable=False)
    users: Mapped[List["User"]] = relationship("User", back_populates="timezone_obj")

    @staticmethod
    def validate_timezone_str(tz_s):
        tz_s = tz_s.strip()
        if tz_s not in pytz.all_timezones:
            raise ValueError(f"'{tz_s}' is not recognized as a valid timezone name.")
        return tz_s

    @sa.orm.validates("timezone")
    def validate_timezone(self, key, value):
        value = TimeZone.validate_timezone_str(value)
        # Prevent renaming of an existing timezone row
        # once inserted (i.e., once `id` is non-None).
        if self.id is not None:
            current = getattr(self, key)
            if current != value:
                raise ValueError(
                    f"Cannot modify timezone name from {current!r} to {value!r} "
                    "because that would affect all users sharing this TimeZone."
                )
        return value

    @staticmethod
    def get_if_exists_or_create_new(timezone):
        with common_sql.get_session() as s:
            existing_tz = s.scalar(
                sa.select(TimeZone).where(TimeZone.timezone == timezone)
            )
            if existing_tz is not None:
                return existing_tz
            else:
                new_tz = TimeZone(timezone=timezone)
                s.add(new_tz)
                s.commit()
                return new_tz


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        sa.CheckConstraint("(`weight` >= 0)", name="non_negative_weight"),
        sa.ForeignKeyConstraint(["gender_id"], ["genders.id"]),
        sa.ForeignKeyConstraint(["activity_level_id"], ["activity_levels.id"]),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.ForeignKeyConstraint(["timezone_id"], ["timezones.id"]),
        sa.UniqueConstraint("telegram_id"),
    )

    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False,
        autoincrement=True
    )
    created_utc_datetime: Mapped[datetime.datetime] = mapped_column(
        mysql.DATETIME, nullable=False
    )
    name: Mapped[str] = mapped_column(mysql.VARCHAR(100), nullable=False)
    telegram_id: Mapped[str] = mapped_column(mysql.VARCHAR(100), nullable=False)
    is_activated: Mapped[int] = mapped_column(mysql.BOOLEAN(), default=True, nullable=False)
    timezone_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), default=1, nullable=False)
    gender_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    goal_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    activity_level_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)


    weight: Mapped[decimal.Decimal] = mapped_column(mysql.DECIMAL(5, 1), nullable=False)
    height: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    date_of_birth: Mapped[datetime.date] = mapped_column(mysql.DATE, nullable=False)
    last_birthday_congratulated: Mapped[mysql.YEAR] = mapped_column(
        mysql.YEAR, nullable=True
    )

    gender_obj: Mapped["Gender"] = relationship("Gender", back_populates="users", lazy="joined")
    goal_obj: Mapped["Goal"] = relationship("Goal", back_populates="users", lazy="joined")
    activity_level_obj: Mapped["ActivityLevel"] = relationship(
        "ActivityLevel", back_populates="users", lazy="joined"
    )
    timezone_obj: Mapped["TimeZone"] = relationship(
        "TimeZone", back_populates="users", lazy="joined"
    )
    meals_eaten: Mapped[List["MealEaten"]] = relationship(
        "MealEaten", back_populates="user", cascade="all, delete-orphan"
    )
    meals_for_future_use: Mapped[List["MealForFutureUse"]] = relationship(
        "MealForFutureUse", back_populates="users", cascade="all, delete-orphan"
    )
    user_target_obj: Mapped["UserTarget"] = relationship(
        "UserTarget", back_populates="user", lazy="joined",
        cascade="all, delete-orphan"
    )

    def get_datetime_now(self):
        now = datetime.datetime.now(
            tz=pytz.timezone(self.timezone_obj.timezone)
        )
        return now

    def get_age(self):
        now = self.get_datetime_now()
        date_now = now.date()
        years_diff = date_now.year - self.date_of_birth.year
        if (
            date_now.month < self.date_of_birth.month or
            (date_now.month == self.date_of_birth.month and date_now.day < self.date_of_birth.day)
        ):
            years_diff -= 1
        return years_diff

    def describe(self):
        description = (
            "User Data:\n"
            f" - Name: {self.name}\n"
            f" - Gender: {self.gender_obj.gender}\n"
            f" - Date of birth: {self.date_of_birth.strftime('%d/%m/%Y')}\n"
            f" - Height: {self.height} cm\n"
            f" - Weight: {self.weight} kg\n"
            f" - Goal: {self.goal_obj.goal}\n"
            f" - Time zone: {self.timezone_obj.timezone}\n"
            f" - Unique telegram id: {self.telegram_id}"
        )
        return description


class MealEaten(Base):
    __tablename__ = "meals_eaten"
    __table_args__ = (
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False,
        autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    created_utc_datetime: Mapped[datetime.datetime] = mapped_column(
        mysql.DATETIME, nullable=False
    )
    created_local_datetime: Mapped[datetime.datetime] = mapped_column(mysql.DATETIME, nullable=False)
    name: Mapped[str] = mapped_column(mysql.VARCHAR(100), nullable=False)
    weight: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    calories: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    carbs: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    protein: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    fat: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    description: Mapped[Optional[str]] = mapped_column(mysql.VARCHAR(5000))

    user: Mapped["User"] = relationship("User", back_populates="meals_eaten")

    def nutrition_as_dict(self):
        return NutritionType.nutrition_as_dict(self)

    def describe(self, long_format=True):
        if long_format:
            return self.describe_long()
        else:
            return self.describe_short()

    def describe_short(self):
        description = (
            "Meal data:\n"
            f" - Name: {self.name}\n"
            f" - Description: {self.description}\n"
            f"Energy / Fat / Carbs / Prot / Weight\n"
            f"{self.calories:.1f} / {self.fat:.1f} / {self.carbs:.1f} / "
            f"{self.protein:.1} / {self.weight:.1f}"
        )
        return description

    def describe_long(self):
        if self.created_local_datetime is not None:
            time_entry = self.created_local_datetime.isoformat(sep=' ', timespec='seconds')
            time_line = f" - Saved At: {time_entry}\n"
        else:
            time_line = ""

        total_nutrition = self.fat + self.carbs + self.protein
        if total_nutrition > 0:
            p_fat = self.fat / total_nutrition * 100
            p_carbs = self.carbs / total_nutrition * 100
            p_protein = self.protein / total_nutrition * 100
        else:
            p_fat = p_carbs = p_protein = 0

        description = (
            "Meal data:\n"
            f" - Name: {self.name}\n"
            f" - Description: {self.description}\n"
            f"{time_line}"
            f" - Calories: {self.calories:.1f} kcal\n"
            f" - Fat: {self.fat:.1f} g ({p_fat:.0f}%)\n"
            f" - Carbs: {self.carbs:.1f} g ({p_carbs:.0f}%)\n"
            f" - Protein: {self.protein:.1f} g ({p_protein:.0f}%)\n"
            f" - Weight: {self.weight:.1f} g"
        )
        return description


class NutritionType(Enum):
    CALORIES = "Calories"
    FAT = "Fat"
    CARBS = "Carbs"
    PROTEIN = "Protein"
    WEIGHT = "Weight"

    @staticmethod
    def without_weight():
        return [n for n in NutritionType if n != NutritionType.WEIGHT]

    def calories(self):
        # 1g protein = 4 kcal, 1g carbs = 4 kcal, 1g fat = 9 kcal
        if self == NutritionType.CALORIES:
            return 1
        elif self == NutritionType.FAT:
            return 9
        elif self == NutritionType.CARBS:
            return 4
        elif self == NutritionType.PROTEIN:
            return 4
        else:
            raise ValueError(f"Calories value not defined for {self}")

    def unit(self):
        if self == NutritionType.CALORIES:
            return "kcal"
        else:
            return "g"

    @staticmethod
    def nutrition_as_dict(meal: MealEaten):
        return {
            NutritionType.CALORIES: meal.calories,
            NutritionType.FAT: meal.fat,
            NutritionType.PROTEIN: meal.protein,
            NutritionType.CARBS: meal.carbs,
            NutritionType.WEIGHT: meal.weight
        }

    @staticmethod
    def sum_nutrition_as_dict(meals: list[MealEaten]):
        return {
            NutritionType.CALORIES: sum([m.calories for m in meals]),
            NutritionType.FAT: sum([m.fat for m in meals]),
            NutritionType.PROTEIN: sum([m.protein for m in meals]),
            NutritionType.CARBS: sum([m.carbs for m in meals]),
            NutritionType.WEIGHT: sum([m.weight for m in meals])
        }


class MealForFutureUse(Base):
    __tablename__ = "meals_for_future_use"
    __table_args__ = (
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False,
        autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    created_utc_datetime: Mapped[datetime.datetime] = mapped_column(
        mysql.DATETIME, nullable=False
    )
    name: Mapped[str] = mapped_column(mysql.VARCHAR(100), nullable=False)
    default_weight_grams: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    calories_per_100g: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    protein_per_100g: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    fat_per_100g: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    carbs_per_100g: Mapped[decimal.Decimal] = mapped_column(
        mysql.DECIMAL(10, 4), nullable=False, default=0
    )
    description: Mapped[Optional[str]] = mapped_column(mysql.VARCHAR(5000))

    users: Mapped["User"] = relationship("User", back_populates="meals_for_future_use")


class UserTarget(Base):
    __tablename__ = "users_targets"
    __table_args__ = (
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id"),
    )

    class Type(Enum):
        MAXIMUM = "MAXIMUM"
        MINIMUM = "MINIMUM"

    id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    calories: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    protein: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    fat: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    carbs: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    target_type: Mapped[str] = mapped_column(
        mysql.ENUM(*[t.value for t in Type]), nullable=False
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="user_target_obj",
    )

    def describe(self):
        if self.target_type == UserTarget.Type.MAXIMUM.value:
            type_description = "Consume no more than the following amount"
        else:
            type_description = "Consume at least the following amount"

        total_nutrition = self.fat + self.carbs + self.protein
        if total_nutrition > 0:
            p_fat = self.fat / total_nutrition * 100
            p_carbs = self.carbs / total_nutrition * 100
            p_protein = self.protein / total_nutrition * 100
        else:
            p_fat = p_carbs = p_protein = 0

        description = (
            f"Nutrition target:\n"
            f"{type_description}\n"
            f" - Calories: {self.calories:.1f} kcal\n"
            f" - Fat: {self.fat:.1f} g ({p_fat:.0f}%)\n"
            f" - Carbs: {self.carbs:.1f} g ({p_carbs:.0f}%)\n"
            f" - Protein: {self.protein:.1f} g ({p_protein:.0f}%)"
        )
        return description
