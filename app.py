


from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)

import os


from datetime import date
from database import (
    supabase,
    login_employee,
    mark_punch_in,
    mark_punch_out,
    check_location,
    already_punched_today,
    save_photo_url,
    save_photo_out_url,
    upload_photo,
    get_today_attendance,
    apply_leave,
    get_leave_requests,
    approve_leave,
    reject_leave,
    get_employee_leaves,
    get_employee,
    get_employees,
    add_employee,
    mark_employee_left,
    reactivate_employee,
    get_leave_balance,
    get_leave_days_in_year,
    
    add_holiday,
    get_holidays,
    deactivate_holiday,
    activate_holiday,
    get_active_holidays,
    get_attendance_report
)

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key"
)

@app.route("/")
def home():

    return render_template(
        "login.html"
    )


@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]

    employee = login_employee(
        username,
        password
    )

    if employee:
    
        session["employee_id"] = (
            employee["id"]
        )
        session["is_admin"] = employee["is_admin"]

        session["full_name"] = employee["full_name"]
        attendance = get_today_attendance(
                employee["id"]
        )
    
        return render_template(
            "dashboard.html",
            employee=employee,
            attendance=attendance
        )
    
    return "Invalid username or password"


@app.route("/punch_in", methods=["POST"])
def punch_in():

    if "employee_id" not in session:
        return redirect("/")

    data = request.get_json(
        silent=True
    ) or {}

    employee_id = session[
        "employee_id"
    ]

    latitude = data["latitude"]
    longitude = data["longitude"]
    photo = data["photo"]
    
    employee_response = (
        supabase.table(
            "employees"
        )
        .select("*")
        .eq(
            "id",
            employee_id
        )
        .execute()
    )
    
    employee = (
        employee_response
        .data[0]
    )
    allowed = check_location(
        employee,
        latitude,
        longitude
    )

    if not allowed:

        return (
            "❌ Outside office location"
        )

    if already_punched_today(
            employee_id):
    
        return (
            "⚠️ Already punched in today"
        )
    
    mark_punch_in(
        employee_id
    )
    
    photo_url = upload_photo(
        employee_id,
        photo
    )
    
    save_photo_url(
        employee_id,
        photo_url
    )
    
    attendance = (
        get_today_attendance(
            employee_id
        )
    )
    
    return render_template(
        "dashboard.html",
        employee=employee,
        attendance=attendance
    )

@app.route(
    "/punch_out",
    methods=["POST"]
)
def punch_out():

    if "employee_id" not in session:
        return redirect("/")

    data = request.get_json(
        silent=True
    ) or {}

    employee_id = session[
        "employee_id"
    ]

    latitude = data["latitude"]
    longitude = data["longitude"]

    photo = data["photo"]

    employee_response = (
        supabase.table(
            "employees"
        )
        .select("*")
        .eq(
            "id",
            employee_id
        )
        .execute()
    )
    
    employee = (
        employee_response
        .data[0]
    )
    allowed = check_location(
        employee,
        latitude,
        longitude
    )

    if not allowed:

        return (
            "❌ Outside office location"
        )

    result = mark_punch_out(
        employee_id
    )

    if result != (
        "Punch out successful"
    ):
        return result

    photo_url = upload_photo(
        employee_id,
        photo
    )

    save_photo_out_url(
        employee_id,
        photo_url
    )

    attendance = (
        get_today_attendance(
            employee_id
        )
    )
    
    return render_template(
        "dashboard.html",
        employee=employee,
        attendance=attendance
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/leave")
def leave():
    if "employee_id" not in session:
        return redirect("/")

    return render_template(
        "leave.html"
    )


@app.route("/dashboard")
def dashboard():

    if "employee_id" not in session:
        return redirect("/")

    employee_id = session.get(
        "employee_id"
    )

    if not employee_id:
        return redirect("/")

    employee_response = (
        supabase.table(
            "employees"
        )
        .select("*")
        .eq(
            "id",
            employee_id
        )
        .execute()
    )

    employee = (
        employee_response.data[0]
    )

    attendance = (
        get_today_attendance(
            employee_id
        )
    )

    return render_template(
        "dashboard.html",
        employee=employee,
        attendance=attendance
    )

@app.route(
    "/submit_leave",
    methods=["POST"]
)
def submit_leave():
    if "employee_id" not in session:
        return redirect("/")
    
    employee_id = (
        session["employee_id"]
    )

    leave_type = (
        request.form["leave_type"]
    )

    from_date = (
        request.form["from_date"]
    )

    to_date = (
        request.form["to_date"]
    )
    from datetime import date

    from_date_value = date.fromisoformat(
        from_date
    )

    to_date_value = date.fromisoformat(
        to_date
    )

    if to_date_value < from_date_value:
        return (
            "To Date cannot be before From Date"
        )

    leave_days = (
        get_leave_days_in_year(
            {
                "from_date": from_date,
                "to_date": to_date
            },
            date.today().year
        )
    )

    if leave_days == 0:
        return (
            "Leave request must be within the current leave cycle"
        )
    
    balance = get_leave_balance(employee_id)

    if leave_type == "CL":
    
        if leave_days > balance[
            "cl_remaining"
        ]:
    
            return (
                f"❌ Only "
                f'{balance["cl_remaining"]} '
                f"CL days remaining"
            )


    if leave_type == "SL":

        if leave_days > balance[
            "sl_remaining"
        ]:
    
            return (
                f"❌ Only "
                f'{balance["sl_remaining"]} '
                f"SL days remaining"
            )
        
    reason = (
        request.form["reason"]
    )
    
    apply_leave(

        employee_id,

        leave_type,

        from_date,

        to_date,

        reason
    )

    return """
    <h2>
        Leave Request Submitted
    </h2>

    <a href='/dashboard'>
        Back to Dashboard
    </a>
    """
@app.route("/admin_leaves")
def admin_leaves():
    if "employee_id" not in session:
        return redirect("/")
    
    if not session.get("is_admin"):
        return "Access Denied"

    leaves = get_leave_requests()

    return render_template(
        "admin_leaves.html",
        leaves=leaves
    )

@app.route("/admin_holidays")
def admin_holidays():

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    holidays = get_holidays()

    return render_template(

        "admin_holidays.html",

        holidays=holidays
    )

@app.route("/admin_employees")
def admin_employees():

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    employees = get_employees()

    return render_template(

        "admin_employees.html",

        employees=employees
    )

@app.route(
    "/add_employee",
    methods=["POST"]
)
def add_employee_route():

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    add_employee(

        request.form["full_name"],

        request.form["username"],

        request.form["password"],

        request.form["centre"],

        request.form["joining_date"],

        float(request.form["latitude"]),

        float(request.form["longitude"]),

        int(request.form["allowed_radius"]),

        request.form.get("is_admin") == "on"
    )

    return redirect(
        "/admin_employees"
    )

@app.route(
    "/mark_employee_left/<int:employee_id>",
    methods=["POST"]
)
def mark_employee_left_route(
    employee_id
):

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    mark_employee_left(

        employee_id,

        request.form["last_office_day"]
    )

    return redirect(
        "/admin_employees"
    )

@app.route(
    "/reactivate_employee/<int:employee_id>",
    methods=["POST"]
)
def reactivate_employee_route(
    employee_id
):

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    reactivate_employee(
        employee_id
    )

    return redirect(
        "/admin_employees"
    )

@app.route(
    "/add_holiday",
    methods=["POST"]
)
def add_holiday_route():

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    holiday_date = (
        request.form["holiday_date"]
    )

    holiday_name = (
        request.form["holiday_name"]
    )

    holiday_type = (
        request.form["holiday_type"]
    )

    add_holiday(

        holiday_date,

        holiday_name,

        holiday_type,

        session["full_name"]
    )

    return redirect(
        "/admin_holidays"
    )

@app.route(
    "/deactivate_holiday/<int:holiday_id>",
    methods=["POST"]
)
def deactivate_holiday_route(
    holiday_id
):

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    deactivate_holiday(
        holiday_id
    )

    return redirect(
        "/admin_holidays"
    )

@app.route(
    "/activate_holiday/<int:holiday_id>",
    methods=["POST"]
)
def activate_holiday_route(
    holiday_id
):

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    activate_holiday(
        holiday_id
    )

    return redirect(
        "/admin_holidays"
    )

@app.route(
    "/approve_leave/<int:leave_id>",
    methods=["POST"]
)
def approve_leave_route(
    leave_id
):

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"
    
    approve_leave(
        leave_id,
        session["full_name"]
    )

    return redirect(
        "/admin_leaves"
    )

@app.route(
    "/reject_leave/<int:leave_id>",
    methods=["POST"]
)
def reject_leave_route(
    leave_id
):

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    reject_leave(
        leave_id,
        session["full_name"]
    )

    return redirect(
        "/admin_leaves"
    )

@app.route("/my_leaves")
def my_leaves():

    if "employee_id" not in session:

        return redirect("/")

    employee_id = session["employee_id"]

    leaves = get_employee_leaves(
        employee_id
    )

    from datetime import date

    today = date.today()

    balance = get_leave_balance(
        employee_id
    )

    cl_remaining = balance[
        "cl_remaining"
    ]

    sl_remaining = balance[
        "sl_remaining"
    ]

    total_cl = balance[
        "total_cl"
    ]

    total_sl = balance[
        "total_sl"
    ]

    eligible_months = balance[
        "eligible_months"
    ]

    approved = 0
    
    for leave in leaves:
    
        if leave["status"] == "Approved":
    
            leave_days = get_leave_days_in_year(
                leave,
                today.year
            )
    
            approved += leave_days
    pending = len([
        leave
        for leave in leaves
        if leave["status"] == "Pending"
    ])

    rejected = len([
        leave
        for leave in leaves
        if leave["status"] == "Rejected"
    ])

    return render_template(
    
        "my_leaves.html",
    
        leaves=leaves,
    
        approved=approved,
    
        pending=pending,
    
        rejected=rejected,
    
        cl_remaining=cl_remaining,
    
        sl_remaining=sl_remaining,
    
        total_cl=total_cl,
    
        total_sl=total_sl,

        eligible_months=eligible_months
    )

@app.route("/holidays")
def holidays():

    if "employee_id" not in session:

        return redirect("/")

    holidays = get_active_holidays()

    return render_template(

        "holidays.html",

        holidays=holidays
    )

@app.route("/admin_attendance")
def admin_attendance():

    if "employee_id" not in session:
        return redirect("/")

    if not session.get("is_admin"):
        return "Access Denied"

    from_date = request.args.get(
    "from_date"
    )
    
    to_date = request.args.get(
        "to_date"
    )
    
    attendance = get_attendance_report(
        from_date,
        to_date
    )

    return render_template(
        "admin_attendance.html",
        attendance=attendance,
        from_date=from_date,
        to_date=to_date
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False
    )
