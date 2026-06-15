
from geopy.distance import geodesic
import base64
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