from typing import List, Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKeyConstraint, Index, String, text
from sqlalchemy.dialects.mysql import DECIMAL, INTEGER, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
import decimal


class Base(DeclarativeBase):
    pass


class Genders(Base):
    __tablename__ = "genders"
    __table_args__ = (
        Index("gender", "gender", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    gender: Mapped[str] = mapped_column(String(50))

    users: Mapped[List["Users"]] = relationship("Users", back_populates="genders")


class Goals(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("goal", "goal", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    goal: Mapped[str] = mapped_column(String(200))

    users: Mapped[List["Users"]] = relationship("Users", back_populates="goals")


class Timezones(Base):
    __tablename__ = "timezones"
    __table_args__ = (
        Index("time_zone", "time_zone", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    time_zone: Mapped[str] = mapped_column(String(200))

    users: Mapped[List["Users"]] = relationship("Users", back_populates="timezones")


class Users(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("(`weight` >= 0)", name="users_chk_1"),
        ForeignKeyConstraint(["gender_id"], ["genders.id"], name="users_ibfk_2"),
        ForeignKeyConstraint(["goal_id"], ["goals.id"], name="users_ibfk_3"),
        ForeignKeyConstraint(["time_zone_id"], ["timezones.id"], name="users_ibfk_1"),
        Index("gender_id", "gender_id"),
        Index("goal_id", "goal_id"),
        Index("telegram_id", "telegram_id", unique=True),
        Index("time_zone_id", "time_zone_id")
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    created_utc_date_time: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text("(utc_timestamp())"))
    name: Mapped[str] = mapped_column(String(100))
    telegram_id: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[int] = mapped_column(TINYINT(1), server_default=text("'0'"))
    time_zone_id: Mapped[int] = mapped_column(INTEGER, server_default=text("'0'"))
    gender_id: Mapped[int] = mapped_column(INTEGER)
    goal_id: Mapped[int] = mapped_column(INTEGER)
    weight: Mapped[decimal.Decimal] = mapped_column(DECIMAL(5, 1))
    height: Mapped[int] = mapped_column(INTEGER)
    date_of_birth: Mapped[datetime.date] = mapped_column(Date)

    genders: Mapped["Genders"] = relationship("Genders", back_populates="users")
    goals: Mapped["Goals"] = relationship("Goals", back_populates="users")
    timezones: Mapped["Timezones"] = relationship("Timezones", back_populates="users")
    meals_eaten: Mapped[List["MealsEaten"]] = relationship("MealsEaten", back_populates="users")
    meals_for_future_use: Mapped[List["MealsForFutureUse"]] = relationship("MealsForFutureUse", back_populates="users")
    users_targets: Mapped[List["UsersTargets"]] = relationship("UsersTargets", back_populates="users")


class MealsEaten(Base):
    __tablename__ = "meals_eaten"
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="meals_eaten_ibfk_1"),
        Index("user_id", "user_id")
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    user_id: Mapped[int] = mapped_column(INTEGER)
    created_utc_date_time: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text("(utc_timestamp())"))
    created_local_date_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    name: Mapped[str] = mapped_column(String(100))
    weight: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    calories: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    carbs: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    protein: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    fat: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    description: Mapped[Optional[str]] = mapped_column(String(5000))

    users: Mapped["Users"] = relationship("Users", back_populates="meals_eaten")


class MealsForFutureUse(Base):
    __tablename__ = "meals_for_future_use"
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="meals_for_future_use_ibfk_1"),
        Index("user_id", "user_id", "name", unique=True)
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    user_id: Mapped[int] = mapped_column(INTEGER)
    created_utc_date_time: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text("(utc_timestamp())"))
    name: Mapped[str] = mapped_column(String(100))
    default_weight_grams: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    calories_per_100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    protein_per_100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    fat_per_100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    carbs_per_100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    description: Mapped[Optional[str]] = mapped_column(String(5000))

    users: Mapped["Users"] = relationship("Users", back_populates="meals_for_future_use")


class UsersTargets(Base):
    __tablename__ = "users_targets"
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="users_targets_ibfk_1"),
        Index("user_id", "user_id", unique=True)
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    user_id: Mapped[int] = mapped_column(INTEGER)
    calories: Mapped[int] = mapped_column(INTEGER)
    protein: Mapped[int] = mapped_column(INTEGER)
    fat: Mapped[int] = mapped_column(INTEGER)
    carbs: Mapped[int] = mapped_column(INTEGER)
    meal_utc_date_time: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text("(utc_timestamp())"))

    users: Mapped["Users"] = relationship("Users", back_populates="users_targets")
