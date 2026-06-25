
from geopy.distance import geodesic
import base64
from math import ceil
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import date

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def login_employee(username, password):

    response = supabase.table(
        "employees"
    ).select(
        "*"
    ).eq(
        "username", username
    ).eq(
        "password", password
    ).eq(
        "is_active", True
    ).execute()

    if len(response.data) > 0:
        return response.data[0]

    return None


def mark_punch_in(employee_id):

    today = str(
        date.today()
    )

    current_time = str(
        datetime.now(
            ZoneInfo(
                "Asia/Kolkata"
            )
        )
    )
    response = supabase.table(
        "attendance"
    ).insert(
        {
            "employee_id":
                employee_id,

            "attendance_date":
                today,

            "punch_in":
                current_time,

            "status":
                "Present"
        }
    ).execute()

    return response

def check_location(employee, user_lat, user_long):

    office_location = (
        employee["latitude"],
        employee["longitude"]
    )

    employee_location = (
        user_lat,
        user_long
    )

    distance = geodesic(
        office_location,
        employee_location
    ).meters

    print(
        "Distance:",
        distance
    )

    if distance <= employee["allowed_radius"]:
        return True

    return False

def already_punched_today(
        employee_id):

    today = str(
        date.today()
    )

    response = supabase.table(
        "attendance"
    ).select(
        "*"
    ).eq(
        "employee_id",
        employee_id
    ).eq(
        "attendance_date",
        today
    ).execute()

    if len(
        response.data
    ) > 0:

        return True

    return False

def mark_punch_out(
        employee_id):

    today = str(
        date.today()
    )

    response = supabase.table(
        "attendance"
    ).select(
        "*"
    ).eq(
        "employee_id",
        employee_id
    ).eq(
        "attendance_date",
        today
    ).execute()

    if len(
        response.data
    ) == 0:

        return (
            "No punch in found"
        )

    attendance = (
        response.data[0]
    )

    if attendance[
            "punch_out"]:

        return (
            "Already punched out"
        )

    punch_in_time = (
        datetime.fromisoformat(
            attendance[
                "punch_in"
            ]
        )
    )
    
    if (
        punch_in_time.tzinfo
        is None
    ):
    
        punch_in_time = (
            punch_in_time
            .replace(
                tzinfo=ZoneInfo(
                    "Asia/Kolkata"
                )
            )
        )
    
    punch_out_time = (
        datetime.now(
            ZoneInfo(
                "Asia/Kolkata"
            )
        )
    )
    total_hours = (
        punch_out_time
        -
        punch_in_time
    ).total_seconds() / 3600


    supabase.table(
        "attendance"
    ).update(
        {
            "punch_out":
                punch_out_time
                .isoformat(),

            "total_hours":
                round(
                    total_hours,
                    2
                )
        }
    ).eq(
        "id",
        attendance["id"]
    ).execute()

    return (
        "Punch out successful"
    )

def save_photo_url(
        employee_id,
        photo_url):

    today = str(
        date.today()
    )

    supabase.table(
        "attendance"
    ).update(
        {
            "photo_in":
                photo_url
        }
    ).eq(
        "employee_id",
        employee_id
    ).eq(
        "attendance_date",
        today
    ).execute()
        
        
def upload_photo(
        employee_id,
        image_data):

    base64_data = (
        image_data
        .split(",")[1]
    )

    image_bytes = (
        base64.b64decode(
            base64_data
        )
    )

    file_name = (
        f"{employee_id}_"
        f"{datetime.now().timestamp()}"
        ".jpg"
    )

    supabase.storage.from_(
        "attendance-photos"
    ).upload(
        file_name,
        image_bytes
    )

    photo_url = (
        supabase.storage
        .from_(
            "attendance-photos"
        )
        .get_public_url(
            file_name
        )
    )

    return photo_url

def save_photo_out_url(
        employee_id,
        photo_url):

    today = str(
        date.today()
    )

    supabase.table(
        "attendance"
    ).update(
        {
            "photo_out":
                photo_url
        }
    ).eq(
        "employee_id",
        employee_id
    ).eq(
        "attendance_date",
        today
    ).execute()
        
        
def get_today_attendance(
        employee_id):

    today = str(
        date.today()
    )

    response = supabase.table(
        "attendance"
    ).select(
        "*"
    ).eq(
        "employee_id",
        employee_id
    ).eq(
        "attendance_date",
        today
    ).execute()

    if len(
        response.data
    ) > 0:

        return (
            response.data[0]
        )

    return None


def apply_leave(
    employee_id,
    leave_type,
    from_date,
    to_date,
    reason
):

    response = (
        supabase.table(
            "leave_requests"
        )
        .insert({

            "employee_id": employee_id,

            "leave_type": leave_type,

            "from_date": from_date,

            "to_date": to_date,

            "reason": reason,

            "status": "Pending"

        })
        .execute()
    )

    return response


def get_leave_requests():

    response = (
        supabase.table(
            "leave_requests"
        )
        .select("*")
        .order(
            "applied_on",
            desc=True
        )
        .execute()
    )

    return response.data

from datetime import datetime

def approve_leave(
    leave_id,
    approved_by
):

    return (
        supabase.table(
            "leave_requests"
        )
        .update({

            "status": "Approved",

            "approved_by": approved_by,

            "approved_on":
                datetime.now().isoformat()

        })
        .eq(
            "id",
            leave_id
        )
        .execute()
    )
        
from datetime import datetime

def reject_leave(
    leave_id,
    approved_by
):

    return (
        supabase.table(
            "leave_requests"
        )
        .update({

            "status": "Rejected",

            "approved_by": approved_by,

            "approved_on":
                datetime.now().isoformat()

        })
        .eq(
            "id",
            leave_id
        )
        .execute()
    )
        
        
def get_employee_leaves(
    employee_id
):

    response = (
        supabase.table(
            "leave_requests"
        )
        .select("*")
        .eq(
            "employee_id",
            employee_id
        )
        .order(
            "applied_on",
            desc=True
        )
        .execute()
    )

    return response.data


def get_employee(
    employee_id
):

    response = (
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

    return response.data[0]


def get_employees():

    response = (
        supabase.table(
            "employees"
        )
        .select("*")
        .order(
            "full_name"
        )
        .execute()
    )

    return response.data


def add_employee(
    full_name,
    username,
    password,
    centre,
    joining_date,
    latitude,
    longitude,
    allowed_radius,
    is_admin
):

    response = (
        supabase.table(
            "employees"
        )
        .insert({

            "full_name": full_name,

            "username": username,

            "password": password,

            "centre": centre,

            "joining_date": joining_date,

            "latitude": latitude,

            "longitude": longitude,

            "allowed_radius": allowed_radius,

            "is_admin": is_admin,

            "is_active": True

        })
        .execute()
    )

    return response


def mark_employee_left(
    employee_id,
    last_office_day
):

    response = (
        supabase.table(
            "employees"
        )
        .update({

            "is_active": False,

            "last_office_day": last_office_day

        })
        .eq(
            "id",
            employee_id
        )
        .execute()
    )

    return response


def reactivate_employee(
    employee_id
):

    response = (
        supabase.table(
            "employees"
        )
        .update({

            "is_active": True,

            "last_office_day": None

        })
        .eq(
            "id",
            employee_id
        )
        .execute()
    )

    return response


from datetime import date


def get_leave_entitlement(
    employee,
    as_of=None
):

    if as_of is None:
        as_of = date.today()

    joining_date = date.fromisoformat(
        employee["joining_date"]
    )

    service_years = (
        as_of - joining_date
    ).days / 365

    if service_years >= 1:

        annual_cl = 8
        annual_sl = 6

    else:

        annual_cl = 6
        annual_sl = 6

    if joining_date.year == as_of.year:

        eligible_months = (
            12 - joining_date.month + 1
        )

        total_cl = ceil(
            annual_cl * eligible_months / 12
        )

        total_sl = ceil(
            annual_sl * eligible_months / 12
        )

    else:

        eligible_months = 12

        total_cl = annual_cl
        total_sl = annual_sl

    return {

        "annual_cl": annual_cl,

        "annual_sl": annual_sl,

        "eligible_months": eligible_months,

        "total_cl": total_cl,

        "total_sl": total_sl
    }


def get_leave_days_in_year(
    leave,
    year
):

    from_date = date.fromisoformat(
        leave["from_date"]
    )

    to_date = date.fromisoformat(
        leave["to_date"]
    )

    year_start = date(
        year,
        1,
        1
    )

    year_end = date(
        year,
        12,
        31
    )

    start = max(
        from_date,
        year_start
    )

    end = min(
        to_date,
        year_end
    )

    if end < start:

        return 0

    return (
        end - start
    ).days + 1


def get_leave_balance(employee_id):

    employee = (
        supabase.table("employees")
        .select("*")
        .eq("id", employee_id)
        .execute()
        .data[0]
    )

    today = date.today()

    entitlement = get_leave_entitlement(
        employee,
        today
    )

    total_cl = entitlement[
        "total_cl"
    ]

    total_sl = entitlement[
        "total_sl"
    ]

    leaves = (
        supabase.table("leave_requests")
        .select("*")
        .eq("employee_id", employee_id)
        .eq("status", "Approved")
        .execute()
        .data
    )

    approved_cl = 0
    approved_sl = 0

    for leave in leaves:

        leave_days = get_leave_days_in_year(
            leave,
            today.year
        )

        if leave["leave_type"] == "CL":

            approved_cl += leave_days

        elif leave["leave_type"] == "SL":

            approved_sl += leave_days

    return {

        "total_cl":
            total_cl,

        "total_sl":
            total_sl,

        "approved_cl":
            approved_cl,

        "approved_sl":
            approved_sl,

        "eligible_months":
            entitlement["eligible_months"],

        "cl_remaining":
            total_cl - approved_cl,

        "sl_remaining":
            total_sl - approved_sl
    }
        
        
def add_holiday(

    holiday_date,

    holiday_name,

    holiday_type,

    created_by
):

    response = (
        supabase.table(
            "holidays"
        )
        .insert({

            "holiday_date":
                holiday_date,

            "holiday_name":
                holiday_name,

            "holiday_type":
                holiday_type,

            "created_by":
                created_by,

            "is_active":
                True

        })
        .execute()
    )

    return response

def get_holidays():

    response = (
        supabase.table(
            "holidays"
        )
        .select("*")
        .order(
            "holiday_date"
        )
        .execute()
    )

    return response.data

def get_active_holidays():

    response = (
        supabase.table(
            "holidays"
        )
        .select("*")
        .eq(
            "is_active",
            True
        )
        .order(
            "holiday_date"
        )
        .execute()
    )

    return response.data

def deactivate_holiday(
    holiday_id
):

    response = (
        supabase.table(
            "holidays"
        )
        .update({

            "is_active":
                False

        })
        .eq(
            "id",
            holiday_id
        )
        .execute()
    )

    return response


def activate_holiday(
    holiday_id
):

    response = (
        supabase.table(
            "holidays"
        )
        .update({

            "is_active":
                True

        })
        .eq(
            "id",
            holiday_id
        )
        .execute()
    )

    return response
