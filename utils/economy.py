import time
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

# ─────────────────────────
# MONGODB
# ─────────────────────────

MONGO_URI = "YOUR_MONGO_URI"

client = MongoClient(MONGO_URI)

db = client["royal_bot"]

economy_collection = db["economy"]

history_collection = db["history"]

# ─────────────────────────
# ACCOUNT
# ─────────────────────────

def create_account(user_id):

    user = economy_collection.find_one({

        "user_id": str(user_id)

    })

    if user is None:

        economy_collection.insert_one({

            "user_id": str(user_id),

            "cash": 0,

            "daily": 0,

            "weekly": 0,

            "monthly": 0

        })

# ─────────────────────────
# CASH
# ─────────────────────────

def get_cash(user_id):

    create_account(user_id)

    user = economy_collection.find_one({

        "user_id": str(user_id)

    })

    return user.get("cash", 0)


def add_cash(user_id, amount):

    create_account(user_id)

    economy_collection.update_one(

        {

            "user_id": str(user_id)

        },

        {

            "$inc": {

                "cash": amount

            }

        }

    )


def remove_cash(user_id, amount):

    create_account(user_id)

    economy_collection.update_one(

        {

            "user_id": str(user_id)

        },

        {

            "$inc": {

                "cash": -amount

            }

        }

    )

# ─────────────────────────
# FORMAT CASH
# ─────────────────────────

def format_cash(amount):

    amount = int(amount)

    if amount >= 1000000000:

        return f"${amount/1000000000:.1f}B"

    if amount >= 1000000:

        return f"${amount/1000000:.1f}M"

    if amount >= 1000:

        return f"${amount/1000:.1f}K"

    return f"${amount}"

# ─────────────────────────
# PARSE AMOUNT
# ─────────────────────────

def parse_amount(amount):

    amount = str(amount).lower()

    if amount.endswith("k"):

        return int(float(amount[:-1]) * 1000)

    if amount.endswith("m"):

        return int(float(amount[:-1]) * 1000000)

    if amount.endswith("b"):

        return int(float(amount[:-1]) * 1000000000)

    return int(amount)

# ─────────────────────────
# HISTORY
# ─────────────────────────

def add_history(user_id, text):

    history_collection.insert_one({

        "user_id": str(user_id),

        "text": text,

        "time": int(time.time())

    })


def get_history(user_id):

    return list(

        history_collection.find({

            "user_id": str(user_id)

        })

    )

# ─────────────────────────
# IST RESET SYSTEM
# ─────────────────────────

IST = timezone(

    timedelta(hours=5, minutes=30)

)

# ─────────────────────────
# DAILY
# ─────────────────────────

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

    return int(reset.timestamp())


def can_claim_daily(user_id):

    create_account(user_id)

    user = economy_collection.find_one({

        "user_id": str(user_id)

    })

    last_daily = user.get("daily", 0)

    next_reset = get_next_daily_reset()

    previous_reset = next_reset - 86400

    return last_daily < previous_reset


def update_daily(user_id):

    economy_collection.update_one(

        {

            "user_id": str(user_id)

        },

        {

            "$set": {

                "daily": int(time.time())

            }

        }

    )

# ─────────────────────────
# WEEKLY
# ─────────────────────────

def get_next_weekly_reset():

    now = datetime.now(IST)

    day = now.day

    targets = [7, 14, 21, 28]

    next_day = None

    for d in targets:

        if day < d:

            next_day = d

            break

    if next_day is None:

        if now.month == 12:

            reset = datetime(

                now.year + 1,
                1,
                7,
                5,
                30,
                tzinfo=IST
            )

        else:

            reset = datetime(

                now.year,
                now.month + 1,
                7,
                5,
                30,
                tzinfo=IST
            )

    else:

        reset = datetime(

            now.year,
            now.month,
            next_day,
            5,
            30,
            tzinfo=IST
        )

    return int(reset.timestamp())


def can_claim_weekly(user_id):

    create_account(user_id)

    user = economy_collection.find_one({

        "user_id": str(user_id)

    })

    last_weekly = user.get("weekly", 0)

    next_reset = get_next_weekly_reset()

    previous_reset = next_reset - 604800

    return last_weekly < previous_reset


def update_weekly(user_id):

    economy_collection.update_one(

        {

            "user_id": str(user_id)

        },

        {

            "$set": {

                "weekly": int(time.time())

            }

        }

    )

# ─────────────────────────
# MONTHLY
# ─────────────────────────

def get_next_monthly_reset():

    now = datetime.now(IST)

    if now.month == 12:

        reset = datetime(

            now.year + 1,
            1,
            1,
            5,
            30,
            tzinfo=IST
        )

    else:

        reset = datetime(

            now.year,
            now.month + 1,
            1,
            5,
            30,
            tzinfo=IST
        )

    return int(reset.timestamp())


def can_claim_monthly(user_id):

    create_account(user_id)

    user = economy_collection.find_one({

        "user_id": str(user_id)

    })

    last_monthly = user.get("monthly", 0)

    next_reset = get_next_monthly_reset()

    previous_reset = next_reset - 2592000

    return last_monthly < previous_reset


def update_monthly(user_id):

    economy_collection.update_one(

        {

            "user_id": str(user_id)

        },

        {

            "$set": {

                "monthly": int(time.time())

            }

        }

    )
