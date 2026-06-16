


from flask import (
    Flask,
    render_template,
    request,
    redirect
)

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
    get_today_attendance
)

app = Flask(__name__)


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

@app.route(
    "/logout"
)
def logout():

    return redirect(
        "/"
    )

if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False
    )