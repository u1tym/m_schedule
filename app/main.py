import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, time

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db import get_db
from app.logging_setup import configure_logging
from app.middleware_request_log import RequestLoggingMiddleware
from app.models import ActivityCategory, Holiday, Schedule
from app.schemas import (
    ActivityCategoryCreate,
    ActivityCategoryResponse,
    HolidayCreate,
    HolidayResponse,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
    TodoAlertItemResponse,
    build_schedule_response,
    build_todo_alert_item,
    schedule_occupancy_range,
    todo_matches_alert_window,
)

err_log = logging.getLogger("app.error")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(get_settings())
    yield


app = FastAPI(title="m_schedule API", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(HTTPException)
async def logging_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    err_log.warning(
        "HTTPException status=%s detail=%s method=%s path=%s query=%s",
        exc.status_code,
        exc.detail,
        request.method,
        request.url.path,
        request.url.query or "-",
    )
    return await default_http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def logging_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    err_log.warning(
        "RequestValidationError method=%s path=%s query=%s errors=%s body=%s",
        request.method,
        request.url.path,
        request.url.query or "-",
        exc.errors(),
        exc.body,
    )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(Exception)
async def logging_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    err_log.exception(
        "unhandled_exception method=%s path=%s query=%s",
        request.method,
        request.url.path,
        request.url.query or "-",
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def validate_all_day_start(payload_start_datetime: datetime, is_all_day: bool) -> None:
    if is_all_day and payload_start_datetime.time() != time.min:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All-day schedule start_datetime must be 00:00.",
        )


def get_active_category_or_404(db: Session, category_id: int) -> ActivityCategory:
    category: ActivityCategory | None = db.scalar(
        select(ActivityCategory).where(
            ActivityCategory.id == category_id, ActivityCategory.is_deleted.is_(False)
        )
    )
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity category not found.")
    return category


@app.get("/activity-categories", response_model=list[ActivityCategoryResponse])
def list_activity_categories(db: Session = Depends(get_db)) -> list[ActivityCategory]:
    return list(
        db.scalars(
            select(ActivityCategory)
            .where(ActivityCategory.is_deleted.is_(False))
            .order_by(ActivityCategory.id.asc())
        )
    )


@app.post("/activity-categories", response_model=ActivityCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_activity_category(payload: ActivityCategoryCreate, db: Session = Depends(get_db)) -> ActivityCategory:
    category = ActivityCategory(name=payload.name, is_deleted=False)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@app.delete("/activity-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity_category(category_id: int, db: Session = Depends(get_db)) -> None:
    category: ActivityCategory | None = db.scalar(select(ActivityCategory).where(ActivityCategory.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity category not found.")
    if category.is_deleted:
        return
    category.is_deleted = True
    db.add(category)
    db.commit()


@app.get("/holidays", response_model=list[HolidayResponse])
def list_holidays(
    from_date: date | None = Query(default=None, description="YYYY-MM-DD"),
    to_date: date | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
) -> list[Holiday]:
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="from_date must be <= to_date.")

    stmt = select(Holiday)
    if from_date is not None:
        stmt = stmt.where(Holiday.date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Holiday.date <= to_date)
    stmt = stmt.order_by(Holiday.date.asc())
    return list(db.scalars(stmt))


@app.post("/holidays", response_model=HolidayResponse, status_code=status.HTTP_201_CREATED)
def create_holiday(payload: HolidayCreate, db: Session = Depends(get_db)) -> Holiday:
    exists: Holiday | None = db.scalar(select(Holiday).where(Holiday.date == payload.date))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Holiday date already exists.")

    holiday = Holiday(date=payload.date, name=payload.name)
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@app.get("/schedules", response_model=list[ScheduleResponse])
def list_schedules_in_period(
    from_date: date = Query(description="YYYY-MM-DD"),
    to_date: date = Query(description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
) -> list[ScheduleResponse]:
    if from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="from_date must be <= to_date.")

    period_start: datetime = datetime.combine(from_date, time.min)
    period_end: datetime = datetime.combine(to_date, time(hour=23, minute=59))

    schedules = list(
        db.scalars(
            select(Schedule)
            .options(joinedload(Schedule.activity_category))
            .where(Schedule.is_deleted.is_(False))
            .order_by(Schedule.start_datetime.asc(), Schedule.id.asc())
        )
    )

    response: list[ScheduleResponse] = []
    for item in schedules:
        if item.activity_category is None or item.activity_category.is_deleted:
            continue
        occ_start, occ_end = schedule_occupancy_range(
            start_datetime_value=item.start_datetime,
            duration=item.duration,
            is_all_day=item.is_all_day,
        )
        if occ_end >= period_start and occ_start <= period_end:
            response.append(
                build_schedule_response(
                    schedule_id=item.id,
                    title=item.title,
                    activity_category_id=item.activity_category_id,
                    activity_category_name=item.activity_category.name,
                    start_datetime_value=item.start_datetime,
                    duration=item.duration,
                    is_all_day=item.is_all_day,
                    schedule_type=item.schedule_type,  # type: ignore[arg-type]
                    is_todo_completed=item.is_todo_completed,
                )
            )
    return response


@app.get("/schedules/todo-alerts", response_model=list[TodoAlertItemResponse])
def list_todo_alerts(
    ref_date: date = Query(description="基準日（例: 当日） YYYY-MM-DD"),
    db: Session = Depends(get_db),
) -> list[TodoAlertItemResponse]:
    """注意喚起対象の TODO を返す（予定タイプは含めない）。"""
    schedules = list(
        db.scalars(
            select(Schedule)
            .options(joinedload(Schedule.activity_category))
            .where(Schedule.is_deleted.is_(False))
            .order_by(Schedule.start_datetime.asc(), Schedule.id.asc())
        )
    )

    out: list[TodoAlertItemResponse] = []
    for item in schedules:
        if item.activity_category is None or item.activity_category.is_deleted:
            continue
        if not todo_matches_alert_window(
            schedule_type=item.schedule_type,
            is_todo_completed=item.is_todo_completed,
            start_datetime_value=item.start_datetime,
            duration=item.duration,
            is_all_day=item.is_all_day,
            ref_date=ref_date,
        ):
            continue
        out.append(
            build_todo_alert_item(
                schedule_id=item.id,
                title=item.title,
                start_datetime_value=item.start_datetime,
                duration=item.duration,
                is_all_day=item.is_all_day,
                schedule_type=item.schedule_type,  # type: ignore[arg-type]
                is_todo_completed=item.is_todo_completed,
                location=item.location,
                details=item.details,
            )
        )
    return out


@app.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)) -> ScheduleResponse:
    schedule: Schedule | None = db.scalar(
        select(Schedule)
        .options(joinedload(Schedule.activity_category))
        .where(Schedule.id == schedule_id, Schedule.is_deleted.is_(False))
    )
    if schedule is None or schedule.activity_category is None or schedule.activity_category.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    return build_schedule_response(
        schedule_id=schedule.id,
        title=schedule.title,
        activity_category_id=schedule.activity_category_id,
        activity_category_name=schedule.activity_category.name,
        start_datetime_value=schedule.start_datetime,
        duration=schedule.duration,
        is_all_day=schedule.is_all_day,
        schedule_type=schedule.schedule_type,  # type: ignore[arg-type]
        is_todo_completed=schedule.is_todo_completed,
        location=schedule.location,
        details=schedule.details,
    )


@app.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db)) -> ScheduleResponse:
    validate_all_day_start(payload.start_datetime, payload.is_all_day)
    category = get_active_category_or_404(db, payload.activity_category_id)

    schedule = Schedule(
        title=payload.title,
        start_datetime=payload.start_datetime,
        duration=payload.duration,
        is_all_day=payload.is_all_day,
        activity_category_id=payload.activity_category_id,
        schedule_type=payload.schedule_type,
        location=payload.location,
        details=payload.details,
        is_todo_completed=payload.is_todo_completed,
        is_deleted=False,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return build_schedule_response(
        schedule_id=schedule.id,
        title=schedule.title,
        activity_category_id=schedule.activity_category_id,
        activity_category_name=category.name,
        start_datetime_value=schedule.start_datetime,
        duration=schedule.duration,
        is_all_day=schedule.is_all_day,
        schedule_type=schedule.schedule_type,  # type: ignore[arg-type]
        is_todo_completed=schedule.is_todo_completed,
        location=schedule.location,
        details=schedule.details,
    )


@app.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, payload: ScheduleUpdate, db: Session = Depends(get_db)) -> ScheduleResponse:
    validate_all_day_start(payload.start_datetime, payload.is_all_day)
    schedule: Schedule | None = db.scalar(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.is_deleted.is_(False))
    )
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")

    category = get_active_category_or_404(db, payload.activity_category_id)
    schedule.title = payload.title
    schedule.start_datetime = payload.start_datetime
    schedule.duration = payload.duration
    schedule.is_all_day = payload.is_all_day
    schedule.activity_category_id = payload.activity_category_id
    schedule.schedule_type = payload.schedule_type
    schedule.location = payload.location
    schedule.details = payload.details
    schedule.is_todo_completed = payload.is_todo_completed
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return build_schedule_response(
        schedule_id=schedule.id,
        title=schedule.title,
        activity_category_id=schedule.activity_category_id,
        activity_category_name=category.name,
        start_datetime_value=schedule.start_datetime,
        duration=schedule.duration,
        is_all_day=schedule.is_all_day,
        schedule_type=schedule.schedule_type,  # type: ignore[arg-type]
        is_todo_completed=schedule.is_todo_completed,
        location=schedule.location,
        details=schedule.details,
    )


@app.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)) -> None:
    schedule: Schedule | None = db.scalar(select(Schedule).where(Schedule.id == schedule_id))
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    if schedule.is_deleted:
        return
    schedule.is_deleted = True
    db.add(schedule)
    db.commit()
