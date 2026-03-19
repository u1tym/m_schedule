from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCHEDULE_TYPE = Literal["予定", "TODO"]


class ActivityCategoryCreate(BaseModel):
    name: str = Field(min_length=1)


class ActivityCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_deleted: bool


class HolidayCreate(BaseModel):
    date: date
    name: str = Field(min_length=1)


class HolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    name: str


class ScheduleCreate(BaseModel):
    title: str = Field(min_length=1)
    start_datetime: datetime
    duration: int = Field(gt=0)
    is_all_day: bool
    activity_category_id: int
    schedule_type: SCHEDULE_TYPE
    location: str | None = None
    details: str | None = None
    is_todo_completed: bool = False

    @field_validator("start_datetime")
    @classmethod
    def seconds_must_be_zero(cls, value: datetime) -> datetime:
        if value.second != 0 or value.microsecond != 0:
            raise ValueError("start_datetime must have seconds and microseconds as zero.")
        return value


class ScheduleUpdate(BaseModel):
    title: str = Field(min_length=1)
    start_datetime: datetime
    duration: int = Field(gt=0)
    is_all_day: bool
    activity_category_id: int
    schedule_type: SCHEDULE_TYPE
    location: str | None = None
    details: str | None = None
    is_todo_completed: bool = False

    @field_validator("start_datetime")
    @classmethod
    def seconds_must_be_zero(cls, value: datetime) -> datetime:
        if value.second != 0 or value.microsecond != 0:
            raise ValueError("start_datetime must have seconds and microseconds as zero.")
        return value


class ScheduleResponse(BaseModel):
    id: int
    title: str
    activity_category_id: int
    activity_category_name: str
    is_all_day: bool
    start_date: date | None = None
    end_date: date | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    schedule_type: SCHEDULE_TYPE
    is_todo_completed: bool | None = None
    location: str | None = None
    details: str | None = None


def build_schedule_response(
    *,
    schedule_id: int,
    title: str,
    activity_category_id: int,
    activity_category_name: str,
    start_datetime_value: datetime,
    duration: int,
    is_all_day: bool,
    schedule_type: SCHEDULE_TYPE,
    is_todo_completed: bool,
    location: str | None = None,
    details: str | None = None,
) -> ScheduleResponse:
    if is_all_day:
        start_day: date = start_datetime_value.date()
        end_day: date = start_day + timedelta(days=duration - 1)
        return ScheduleResponse(
            id=schedule_id,
            title=title,
            activity_category_id=activity_category_id,
            activity_category_name=activity_category_name,
            is_all_day=True,
            start_date=start_day,
            end_date=end_day,
            schedule_type=schedule_type,
            is_todo_completed=is_todo_completed if schedule_type == "TODO" else None,
            location=location,
            details=details,
        )

    end_datetime_value: datetime = start_datetime_value + timedelta(minutes=duration)
    return ScheduleResponse(
        id=schedule_id,
        title=title,
        activity_category_id=activity_category_id,
        activity_category_name=activity_category_name,
        is_all_day=False,
        start_datetime=start_datetime_value,
        end_datetime=end_datetime_value,
        schedule_type=schedule_type,
        is_todo_completed=is_todo_completed if schedule_type == "TODO" else None,
        location=location,
        details=details,
    )


def schedule_occupancy_range(start_datetime_value: datetime, duration: int, is_all_day: bool) -> tuple[datetime, datetime]:
    if is_all_day:
        start_dt: datetime = datetime.combine(start_datetime_value.date(), time.min)
        end_day: date = start_datetime_value.date() + timedelta(days=duration - 1)
        end_dt: datetime = datetime.combine(end_day, time(hour=23, minute=59))
        return start_dt, end_dt
    start_dt = start_datetime_value
    end_dt = start_datetime_value + timedelta(minutes=duration)
    return start_dt, end_dt
