


from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)


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
    get_leave_balance
)

app = Flask(__name__)
app.secret_key = "kkls_secret_key"

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

    data = request.json

    employee_id = int(
        data["employee_id"]
    )

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

    data = request.json

    employee_id = int(
        data["employee_id"]
    )

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

    leave_days = (
    
        date.fromisoformat(to_date)
    
        - date.fromisoformat(from_date)
    
    ).days + 1
    
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

@app.route(
    "/approve_leave/<int:leave_id>"
)
def approve_leave_route(
    leave_id
):

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
    "/reject_leave/<int:leave_id>"
)
def reject_leave_route(
    leave_id
):

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

    employee = get_employee(
        employee_id
    )

    from datetime import date

    joining_date = date.fromisoformat(
        employee["joining_date"]
    )

    today = date.today()

    service_years = (
        today - joining_date
    ).days / 365

    if service_years >= 1:

        total_cl = 8
        total_sl = 6

    else:

        total_cl = 6
        total_sl = 6

    # ADD THIS PART HERE
    approved_cl = 0
    
    for leave in leaves:
    
        if (
            leave["status"] == "Approved"
            and leave["leave_type"] == "CL"
        ):
    
            from_date = date.fromisoformat(
                leave["from_date"]
            )
    
            to_date = date.fromisoformat(
                leave["to_date"]
            )
    
            leave_days = (
                to_date - from_date
            ).days + 1
    
            approved_cl += leave_days

    approved_sl = 0
    
    for leave in leaves:
    
        if (
            leave["status"] == "Approved"
            and leave["leave_type"] == "SL"
        ):
    
            from_date = date.fromisoformat(
                leave["from_date"]
            )
    
            to_date = date.fromisoformat(
                leave["to_date"]
            )
    
            leave_days = (
                to_date - from_date
            ).days + 1
    
            approved_sl += leave_days

    cl_remaining = (
        total_cl
        - approved_cl
    )

    sl_remaining = (
        total_sl
        - approved_sl
    )

    approved = 0
    
    for leave in leaves:
    
        if leave["status"] == "Approved":
    
            from_date = date.fromisoformat(
                leave["from_date"]
            )
    
            to_date = date.fromisoformat(
                leave["to_date"]
            )
    
            leave_days = (
                to_date - from_date
            ).days + 1
    
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
    
        total_sl=total_sl
    )

if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False
    )