from typing import List, Optional

from sqlalchemy import CheckConstraint, DECIMAL, Date, DateTime, ForeignKeyConstraint, Index, String, text
from sqlalchemy.dialects.mysql import DECIMAL, INTEGER, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
import decimal

class Base(DeclarativeBase):
    pass


class Genders(Base):
    __tablename__ = 'genders'
    __table_args__ = (
        Index('Gender', 'Gender', unique=True),
    )

    ID: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    Gender: Mapped[str] = mapped_column(String(50))

    users: Mapped[List['Users']] = relationship('Users', back_populates='genders')


class Goals(Base):
    __tablename__ = 'goals'
    __table_args__ = (
        Index('Goal', 'Goal', unique=True),
    )

    ID: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    Goal: Mapped[str] = mapped_column(String(200))

    users: Mapped[List['Users']] = relationship('Users', back_populates='goals')


class Timezones(Base):
    __tablename__ = 'timezones'
    __table_args__ = (
        Index('TimeZone', 'TimeZone', unique=True),
    )

    ID: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    TimeZone: Mapped[str] = mapped_column(String(200))

    users: Mapped[List['Users']] = relationship('Users', back_populates='timezones')


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint('(`Weight` >= 0)', name='users_chk_1'),
        ForeignKeyConstraint(['GenderID'], ['genders.ID'], name='users_ibfk_2'),
        ForeignKeyConstraint(['GoalID'], ['goals.ID'], name='users_ibfk_3'),
        ForeignKeyConstraint(['TimeZoneID'], ['timezones.ID'], name='users_ibfk_1'),
        Index('GenderID', 'GenderID'),
        Index('GoalID', 'GoalID'),
        Index('TelegramID', 'TelegramID', unique=True),
        Index('TimeZoneID', 'TimeZoneID')
    )

    ID: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    CreatedUTCDateTime: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text('(utc_timestamp())'))
    Name: Mapped[str] = mapped_column(String(100))
    TelegramID: Mapped[str] = mapped_column(String(100))
    IsActive: Mapped[int] = mapped_column(TINYINT(1), server_default=text("'0'"))
    TimeZoneID: Mapped[int] = mapped_column(INTEGER, server_default=text("'0'"))
    GenderID: Mapped[int] = mapped_column(INTEGER)
    GoalID: Mapped[int] = mapped_column(INTEGER)
    Weight: Mapped[decimal.Decimal] = mapped_column(DECIMAL(5, 1))
    Height: Mapped[int] = mapped_column(INTEGER)
    DateOfBirth: Mapped[datetime.date] = mapped_column(Date)

    genders: Mapped['Genders'] = relationship('Genders', back_populates='users')
    goals: Mapped['Goals'] = relationship('Goals', back_populates='users')
    timezones: Mapped['Timezones'] = relationship('Timezones', back_populates='users')
    meals_eaten: Mapped[List['MealsEaten']] = relationship('MealsEaten', back_populates='users')
    meals_for_future_use: Mapped[List['MealsForFutureUse']] = relationship('MealsForFutureUse', back_populates='users')
    users_targets: Mapped[List['UsersTargets']] = relationship('UsersTargets', back_populates='users')


class MealsEaten(Base):
    __tablename__ = 'meals_eaten'
    __table_args__ = (
        ForeignKeyConstraint(['UserID'], ['users.ID'], name='meals_eaten_ibfk_1'),
        Index('UserID', 'UserID')
    )

    ID: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    UserID: Mapped[int] = mapped_column(INTEGER)
    CreatedUTCDateTime: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text('(utc_timestamp())'))
    CreatedLocalDateTime: Mapped[datetime.datetime] = mapped_column(DateTime)
    Name: Mapped[str] = mapped_column(String(100))
    Weight: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    Calories: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    Carbs: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    Protein: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    Fat: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    Description: Mapped[Optional[str]] = mapped_column(String(5000))

    users: Mapped['Users'] = relationship('Users', back_populates='meals_eaten')


class MealsForFutureUse(Base):
    __tablename__ = 'meals_for_future_use'
    __table_args__ = (
        ForeignKeyConstraint(['UserID'], ['users.ID'], name='meals_for_future_use_ibfk_1'),
        Index('UserID', 'UserID', 'Name', unique=True)
    )

    ID: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    UserID: Mapped[int] = mapped_column(INTEGER)
    CreatedUTCDateTime: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text('(utc_timestamp())'))
    Name: Mapped[str] = mapped_column(String(100))
    DefaultWeightGrams: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    CaloriesPer100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    ProteinPer100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    FatPer100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    CarbsPer100g: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 4))
    Description: Mapped[Optional[str]] = mapped_column(String(5000))

    users: Mapped['Users'] = relationship('Users', back_populates='meals_for_future_use')


class UsersTargets(Base):
    __tablename__ = 'users_targets'
    __table_args__ = (
        ForeignKeyConstraint(['UserID'], ['users.ID'], name='users_targets_ibfk_1'),
        Index('UserID', 'UserID', unique=True)
    )

    ID: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    UserID: Mapped[int] = mapped_column(INTEGER)
    Calories: Mapped[int] = mapped_column(INTEGER)
    Protein: Mapped[int] = mapped_column(INTEGER)
    Fat: Mapped[int] = mapped_column(INTEGER)
    Carbs: Mapped[int] = mapped_column(INTEGER)
    MealUTCDateTime: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text('(utc_timestamp())'))

    users: Mapped['Users'] = relationship('Users', back_populates='users_targets')
