from datetime import timedelta, datetime

from aiogram_calendar import (
    SimpleCalendar,
    get_user_locale
)

async def get_calendar(user_id):
    calendar = SimpleCalendar(
        locale=await get_user_locale(user_id), show_alerts=True
    )
    cur_time = datetime.now()
    calendar.set_dates_range(
        cur_time - timedelta(days=30), cur_time + timedelta(days=120)
    )
    return calendar, cur_time