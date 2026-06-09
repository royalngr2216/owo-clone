from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz

# ─────────────────────────
# MONGODB
# ─────────────────────────

MONGO_URI = "YOUR_MONGO_URI"

client = MongoClient(MONGO_URI)

db = client["royal_bot"]

economy_collection = db["economy"]

IST = pytz.timezone("Asia/Kolkata")

# ─────────────────────────
# ACCOUNT
# ─────────────────────────

def create_account(user_id):

    user = economy_collection.find_one(
        {"user_id": str(user_id)}
    )

    if not user:

        economy_collection.insert_one({

            "user_id": str(user_id),

            "cash": 0,

            "daily": "",

            "weekly": "",

            "monthly": ""

        })

# ─────────────────────────
# CASH
# ─────────────────────────

def get_cash(user_id):

    create_account(user_id)

    user = economy_collection.find_one(
        {"user_id": str(user_id)}
    )

    return user.get("cash", 0)


def add_cash(user_id, amount):

    create_account(user_id)

    economy_collection.update_one(

        {"user_id": str(user_id)},

        {"$inc": {"cash": amount}}

    )


def remove_cash(user_id, amount):

    create_account(user_id)

    user = economy_collection.find_one(
        {"user_id": str(user_id)}
    )

    current_cash = user.get("cash", 0)

    new_cash = max(
        current_cash - amount,
        0
    )

    economy_collection.update_one(

        {"user_id": str(user_id)},

        {"$set": {"cash": new_cash}}

    )

# ─────────────────────────
# FORMAT CASH
# ─────────────────────────

def format_cash(amount):

    if amount >= 1_000_000_000:

        return f"${amount/1_000_000_000:.1f}B"

    if amount >= 1_000_000:

        return f"${amount/1_000_000:.1f}M"

    if amount >= 1_000:

        return f"${amount/1_000:.1f}K"

    return f"${amount}"

# ─────────────────────────
# DAILY
# ─────────────────────────

def can_claim_daily(user_id):

    create_account(user_id)

    user = economy_collection.find_one(
        {"user_id": str(user_id)}
    )

    today = datetime.now(
        IST
    ).strftime("%Y-%m-%d")

    return user.get("daily") != today


def update_daily(user_id):

    today = datetime.now(
        IST
    ).strftime("%Y-%m-%d")

    economy_collection.update_one(

        {"user_id": str(user_id)},

        {"$set": {"daily": today}}

    )


def get_next_daily_reset():

    now = datetime.now(IST)

    reset = now.replace(
        hour=5,
        minute=30,
        second=0,
        microsecond=0
    )

    if now >= reset:

        reset += timedelta(days=1)

    return reset.strftime(
        "%d %B %Y, %I:%M %p IST"
    )

# ─────────────────────────
# WEEKLY
# ─────────────────────────

def can_claim_weekly(user_id):

    create_account(user_id)

    user = economy_collection.find_one(
        {"user_id": str(user_id)}
    )

    now = datetime.now(IST)

    current_week = (
        now.year,
        now.month,
        (now.day - 1) // 7
    )

    return user.get("weekly") != str(current_week)


def update_weekly(user_id):

    now = datetime.now(IST)

    current_week = (
        now.year,
        now.month,
        (now.day - 1) // 7
    )

    economy_collection.update_one(

        {"user_id": str(user_id)},

        {"$set": {"weekly": str(current_week)}}

    )


def get_next_weekly_reset():

    now = datetime.now(IST)

    days = [7, 14, 21, 28]

    for day in days:

        if now.day < day:

            reset = now.replace(
                day=day,
                hour=5,
                minute=30,
                second=0,
                microsecond=0
            )

            return reset.strftime(
                "%d %B %Y, %I:%M %p IST"
            )

    next_month = (
        now.replace(day=1)
        + timedelta(days=32)
    ).replace(day=7)

    next_month = next_month.replace(
        hour=5,
        minute=30,
        second=0,
        microsecond=0
    )

    return next_month.strftime(
        "%d %B %Y, %I:%M %p IST"
    )

# ─────────────────────────
# MONTHLY
# ─────────────────────────

def can_claim_monthly(user_id):

    create_account(user_id)

    user = economy_collection.find_one(
        {"user_id": str(user_id)}
    )

    now = datetime.now(IST)

    current_month = (
        now.year,
        now.month
    )

    return user.get("monthly") != str(current_month)


def update_monthly(user_id):

    now = datetime.now(IST)

    current_month = (
        now.year,
        now.month
    )

    economy_collection.update_one(

        {"user_id": str(user_id)},

        {"$set": {"monthly": str(current_month)}}

    )


def get_next_monthly_reset():

    now = datetime.now(IST)

    if now.month == 12:

        reset = now.replace(
            year=now.year + 1,
            month=1,
            day=1,
            hour=5,
            minute=30,
            second=0,
            microsecond=0
        )

    else:

        reset = now.replace(
            month=now.month + 1,
            day=1,
            hour=5,
            minute=30,
            second=0,
            microsecond=0
        )

    return reset.strftime(
        "%d %B %Y, %I:%M %p IST"
    )
