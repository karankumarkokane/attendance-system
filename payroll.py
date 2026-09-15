import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


def _as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(value)


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_monthly_payroll(
    year, month, employees, attendance, leaves, holidays, compensation_history=None
):
    """Build payroll previews without mutating attendance or payroll data."""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    holiday_dates = {
        _as_date(row["holiday_date"])
        for row in holidays
        if row.get("is_active", True)
    }
    month_working_days = 0
    current = month_start
    while current <= month_end:
        if current.weekday() != 6 and current not in holiday_dates:
            month_working_days += 1
        current += timedelta(days=1)
    attendance_by_employee = {}
    for row in attendance:
        attendance_by_employee.setdefault(str(row["employee_id"]), {})[
            _as_date(row["attendance_date"])
        ] = row

    compensation_by_employee = {}
    for item in compensation_history or []:
        compensation_by_employee.setdefault(str(item["employee_id"]), []).append(item)
    for history in compensation_by_employee.values():
        history.sort(key=lambda item: _as_date(item["effective_from"]))

    approved_leave_dates = {}
    for row in leaves:
        if row.get("status") != "Approved":
            continue
        start = max(_as_date(row["from_date"]), month_start)
        end = min(_as_date(row["to_date"]), month_end)
        current = start
        while current <= end:
            approved_leave_dates.setdefault(str(row["employee_id"]), {})[current] = (
                row.get("leave_type") or "Other"
            )
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
            "cl_days": 0,
            "sl_days": 0,
            "approved_leave_details": [],
            "half_days": 0,
            "unauthorized_absences": [],
            "missing_punches": [],
            "warnings": [],
            "resolved_unpaid_leave_days": 0,
            "compensation_details": [],
        }
        employee_key = str(employee["id"])
        employee_attendance = attendance_by_employee.get(employee_key, {})
        employee_leaves = approved_leave_dates.get(employee_key, {})
        employee_compensation = compensation_by_employee.get(employee_key, [])
        prorated_gross = Decimal("0")
        deduction = Decimal("0")
        deduction_units = Decimal("0")
        segments = {}
        current = active_start
        while current <= active_end:
            if current.weekday() == 6 or current in holiday_dates:
                current += timedelta(days=1)
                continue
            summary["working_days"] += 1
            applicable = None
            for change in employee_compensation:
                if _as_date(change["effective_from"]) <= current:
                    applicable = change
                else:
                    break
            salary = _money(
                applicable.get("salary") if applicable
                else employee.get("salary", employee.get("monthly_salary"))
            )
            designation = (
                applicable.get("designation") if applicable
                else (employee.get("designation") or "Employee")
            )
            day_rate = salary / month_working_days if month_working_days else Decimal("0")
            prorated_gross += day_rate
            segment_key = (str(salary), designation)
            segment = segments.setdefault(segment_key, {
                "designation": designation,
                "salary": salary,
                "from_date": current.isoformat(),
                "to_date": current.isoformat(),
                "eligible_days": 0,
                "earned": Decimal("0"),
            })
            segment["to_date"] = current.isoformat()
            segment["eligible_days"] += 1
            segment["earned"] += day_rate
            row = employee_attendance.get(current)
            if current in employee_leaves:
                summary["paid_leave_days"] += 1
                leave_type = employee_leaves[current]
                if leave_type == "CL":
                    summary["cl_days"] += 1
                elif leave_type == "SL":
                    summary["sl_days"] += 1
                summary["approved_leave_details"].append({
                    "date": current.isoformat(),
                    "leave_type": leave_type,
                })
            elif row is None:
                summary["unauthorized_absences"].append(current.isoformat())
                deduction_units += Decimal("1")
                deduction += day_rate
            elif row.get("status") == "Admin Full Day":
                summary["present_days"] += 1
            elif row.get("status") == "Admin Half Day":
                summary["half_days"] += 1
                deduction_units += Decimal("0.5")
                deduction += day_rate * Decimal("0.5")
            elif row.get("status") == "Admin Paid Leave":
                summary["paid_leave_days"] += 1
            elif row.get("status") == "Admin Unpaid Leave":
                summary["resolved_unpaid_leave_days"] += 1
                deduction_units += Decimal("1")
                deduction += day_rate
            elif not row.get("punch_in") or not row.get("punch_out"):
                summary["missing_punches"].append(current.isoformat())
                deduction_units += Decimal("1")
                deduction += day_rate
            elif float(row.get("total_hours") or 0) < 5:
                summary["half_days"] += 1
                deduction_units += Decimal("0.5")
                deduction += day_rate * Decimal("0.5")
            else:
                summary["present_days"] += 1
            current += timedelta(days=1)

        final_compensation = None
        for change in employee_compensation:
            if _as_date(change["effective_from"]) <= active_end:
                final_compensation = change
        salary = _money(
            final_compensation.get("salary") if final_compensation
            else employee.get("salary", employee.get("monthly_salary"))
        )
        if final_compensation:
            employee["designation"] = final_compensation.get("designation") or "Employee"
        prorated_gross = _money(prorated_gross)
        deduction = _money(deduction)
        summary["compensation_details"] = [
            {
                **segment,
                "salary": float(segment["salary"]),
                "earned": float(_money(segment["earned"])),
            }
            for segment in segments.values()
        ]
        summary["monthly_salary"] = salary
        summary["month_working_days"] = month_working_days
        summary["prorated_gross"] = prorated_gross
        summary["deduction_days"] = deduction_units
        summary["deduction"] = deduction
        summary["net_salary"] = _money(max(Decimal("0"), prorated_gross - deduction))
        salary_missing = any(segment["salary"] <= 0 for segment in segments.values())
        if salary_missing:
            summary["warnings"].append("Monthly salary has not been set")
        if summary["unauthorized_absences"]:
            summary["warnings"].append("Absence without an approved leave request")
        if summary["missing_punches"]:
            summary["warnings"].append("Punch-in or punch-out is missing")
        if summary["half_days"]:
            summary["warnings"].append("Less than 5 hours recorded (half-day)")
        summary["can_finalize"] = bool(
            not salary_missing
            and not summary["unauthorized_absences"]
            and not summary["missing_punches"]
        )
        payroll.append(summary)
    return payroll
