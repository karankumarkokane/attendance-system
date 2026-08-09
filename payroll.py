import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


def _as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(value)


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_monthly_payroll(year, month, employees, attendance, leaves, holidays):
    """Build payroll previews without mutating attendance or payroll data."""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    holiday_dates = {
        _as_date(row["holiday_date"])
        for row in holidays
        if row.get("is_active", True)
    }
    attendance_by_employee = {}
    for row in attendance:
        attendance_by_employee.setdefault(row["employee_id"], {})[
            _as_date(row["attendance_date"])
        ] = row

    approved_leave_dates = {}
    for row in leaves:
        if row.get("status") != "Approved":
            continue
        start = max(_as_date(row["from_date"]), month_start)
        end = min(_as_date(row["to_date"]), month_end)
        current = start
        while current <= end:
            approved_leave_dates.setdefault(row["employee_id"], set()).add(current)
            current += timedelta(days=1)

    payroll = []
    for employee in employees:
        joining = _as_date(employee["joining_date"])
        leaving = _as_date(employee["last_office_day"]) if employee.get("last_office_day") else month_end
        active_start = max(month_start, joining)
        active_end = min(month_end, leaving)
        if active_start > active_end:
            continue

        summary = {
            "employee": employee,
            "working_days": 0,
            "present_days": 0,
            "paid_leave_days": 0,
            "half_days": 0,
            "unauthorized_absences": [],
            "missing_punches": [],
            "warnings": [],
            "resolved_unpaid_leave_days": 0,
        }
        employee_attendance = attendance_by_employee.get(employee["id"], {})
        employee_leaves = approved_leave_dates.get(employee["id"], set())
        current = active_start
        while current <= active_end:
            if current.weekday() == 6 or current in holiday_dates:
                current += timedelta(days=1)
                continue
            summary["working_days"] += 1
            row = employee_attendance.get(current)
            if current in employee_leaves:
                summary["paid_leave_days"] += 1
            elif row is None:
                summary["unauthorized_absences"].append(current.isoformat())
            elif row.get("status") == "Admin Full Day":
                summary["present_days"] += 1
            elif row.get("status") == "Admin Half Day":
                summary["half_days"] += 1
            elif row.get("status") == "Admin Paid Leave":
                summary["paid_leave_days"] += 1
            elif row.get("status") == "Admin Unpaid Leave":
                summary["resolved_unpaid_leave_days"] += 1
            elif not row.get("punch_in") or not row.get("punch_out"):
                summary["missing_punches"].append(current.isoformat())
            elif float(row.get("total_hours") or 0) < 5:
                summary["half_days"] += 1
            else:
                summary["present_days"] += 1
            current += timedelta(days=1)

        salary = _money(employee.get("salary", employee.get("monthly_salary")))
        day_rate = salary / summary["working_days"] if summary["working_days"] else Decimal("0")
        deduction_units = Decimal(
            len(summary["unauthorized_absences"])
            + len(summary["missing_punches"])
            + summary["resolved_unpaid_leave_days"]
        )
        deduction_units += Decimal(summary["half_days"]) * Decimal("0.5")
        deduction = _money(day_rate * deduction_units)
        summary["monthly_salary"] = salary
        summary["deduction_days"] = deduction_units
        summary["deduction"] = deduction
        summary["net_salary"] = _money(max(Decimal("0"), salary - deduction))
        if salary <= 0:
            summary["warnings"].append("Monthly salary has not been set")
        if summary["unauthorized_absences"]:
            summary["warnings"].append("Absence without an approved leave request")
        if summary["missing_punches"]:
            summary["warnings"].append("Punch-in or punch-out is missing")
        if summary["half_days"]:
            summary["warnings"].append("Less than 5 hours recorded (half-day)")
        payroll.append(summary)
    return payroll
