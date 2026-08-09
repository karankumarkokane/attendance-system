import calendar
from datetime import date, timedelta


def _date(value):
    return value if isinstance(value, date) else date.fromisoformat(value)


def build_attendance_history(year, month, attendance, leaves, holidays, today=None):
    today = today or date.today()
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    attendance_by_date = {_date(row["attendance_date"]): row for row in attendance}
    holidays_by_date = {_date(row["holiday_date"]): row for row in holidays}
    leave_by_date = {}
    for leave in leaves:
        current = max(start, _date(leave["from_date"]))
        leave_end = min(end, _date(leave["to_date"]))
        while current <= leave_end:
            leave_by_date[current] = leave.get("leave_type") or "Approved Leave"
            current += timedelta(days=1)

    days = []
    current = start
    while current <= end:
        row = attendance_by_date.get(current)
        status = ""
        status_class = "muted"
        if current in holidays_by_date:
            status = f"Holiday - {holidays_by_date[current].get('holiday_name', '')}"
            if row:
                status += " (Punch recorded)"
        elif current.weekday() == 6:
            status = "Sunday" + (" (Punch recorded)" if row else "")
        elif current in leave_by_date:
            status = leave_by_date[current] + (" (Punch recorded)" if row else "")
            status_class = "success-text"
        elif row and row.get("status") in {
            "Admin Full Day", "Admin Half Day", "Admin Paid Leave", "Admin Unpaid Leave"
        }:
            status = row["status"].replace("Admin ", "")
            status_class = "success-text" if status in {"Full Day", "Paid Leave"} else "danger-text"
        elif row and (not row.get("punch_in") or not row.get("punch_out")):
            status = "Missing Punch"
            status_class = "danger-text"
        elif row and float(row.get("total_hours") or 0) < 5:
            status = "Half Day"
            status_class = "danger-text"
        elif row:
            status = "Present"
            status_class = "success-text"
        elif current >= today:
            status = "Not Marked Yet" if current == today else "Not Due"
        else:
            status = "Absent"
            status_class = "danger-text"
        days.append({
            "date": current,
            "day": current.strftime("%A"),
            "status": status,
            "status_class": status_class,
            "punch_in": row.get("punch_in") if row else None,
            "punch_out": row.get("punch_out") if row else None,
            "total_hours": row.get("total_hours") if row else None,
        })
        current += timedelta(days=1)
    return days
