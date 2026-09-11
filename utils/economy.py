import os
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz

MONGO_URI = os.getenv("MONGO_URI")

# Economy is intentionally kept small. Earnings should feel meaningful
# without jumping into millions after a few commands.
MAX_BET = 100_000
MAX_BALANCE = 100_000_000

client = MongoClient(MONGO_URI)
db = client["royal_bot"]
economy_collection = db["economy"]
IST = pytz.timezone("Asia/Kolkata")


def create_account(user_id):
    user = economy_collection.find_one({"user_id": str(user_id)})
    if not user:
        economy_collection.insert_one({
            "user_id": str(user_id),
            "cash": 0,
            "daily": 0,
            "weekly": 0,
            "monthly": 0,
            "give_sent_today": 0,
            "give_reset": 0,
            "padlock_until": 0,
            "rob_uses": 0,
            "rob_reset": 0,
            "workers": {},
            "inventory": {},
            "claimed_achievements": [],
            "pets": []
        })


def get_cash(user_id):
    user = economy_collection.find_one({"user_id": str(user_id)})
    if not user:
        create_account(user_id)
        return 0
    return user.get("cash", 0)


def add_cash(user_id, amount):
    amount = max(0, int(amount))
    if amount <= 0:
        return
    current = get_cash(user_id)
    new_balance = min(current + amount, MAX_BALANCE)
    economy_collection.update_one(
        {"user_id": str(user_id)},
        {"$set": {"cash": new_balance}}
    )


def remove_cash(user_id, amount):
    amount = max(0, int(amount))
    if amount <= 0:
        return
    economy_collection.update_one(
        {"user_id": str(user_id), "cash": {"$gte": amount}},
        {"$inc": {"cash": -amount}}
    )


def format_cash(amount):
    amount = int(amount)
    if amount >= 1_000_000_000:
        return f"{amount/1_000_000_000:.1f}B NGR"
    if amount >= 1_000_000:
        return f"{amount/1_000_000:.1f}M NGR"
    if amount >= 1_000:
        return f"{amount/1_000:.1f}K NGR"
    return f"{amount} NGR"


def can_claim_daily(user_id):
    user = economy_collection.find_one({"user_id": str(user_id)})
    if not user:
        return True
    last = user.get("daily", 0)
    if last == 0:
        return True
    now = datetime.now(IST)
    reset = now.replace(hour=5, minute=30, second=0, microsecond=0)
    if now < reset:
        reset -= timedelta(days=1)
    return datetime.fromtimestamp(last, IST) < reset


def get_daily_reset():
    now = datetime.now(IST)
    reset = now.replace(hour=5, minute=30, second=0, microsecond=0)
    if now >= reset:
        reset += timedelta(days=1)
    return int(reset.timestamp())


def update_daily(user_id):
    economy_collection.update_one({"user_id": str(user_id)}, {"$set": {"daily": datetime.now().timestamp()}})


def can_claim_weekly(user_id):
    user = economy_collection.find_one({"user_id": str(user_id)})
    if not user:
        return True
    last = user.get("weekly", 0)
    if last == 0:
        return True
    now = datetime.now(IST)
    last_time = datetime.fromtimestamp(last, IST)
    return (now.year, now.isocalendar().week) != (last_time.year, last_time.isocalendar().week)


def get_weekly_reset():
    now = datetime.now(IST)
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    reset = (now + timedelta(days=days_until_monday)).replace(hour=5, minute=30, second=0, microsecond=0)
    return int(reset.timestamp())


def update_weekly(user_id):
    economy_collection.update_one({"user_id": str(user_id)}, {"$set": {"weekly": datetime.now().timestamp()}})


def can_claim_monthly(user_id):
    user = economy_collection.find_one({"user_id": str(user_id)})
    if not user:
        return True
    last = user.get("monthly", 0)
    if last == 0:
        return True
    last_time = datetime.fromtimestamp(last, IST)
    now = datetime.now(IST)
    return now.month != last_time.month or now.year != last_time.year


def get_monthly_reset():
    now = datetime.now(IST)
    if now.month == 12:
        reset = datetime(now.year + 1, 1, 1, 5, 30, tzinfo=IST)
    else:
        reset = datetime(now.year, now.month + 1, 1, 5, 30, tzinfo=IST)
    return int(reset.timestamp())


def update_monthly(user_id):
    economy_collection.update_one({"user_id": str(user_id)}, {"$set": {"monthly": datetime.now().timestamp()}})


def parse_amount(amount, balance=None):
    amount = str(amount).lower().strip()
    if amount == "all":
        return balance if balance is not None else None
    try:
        if amount.endswith("k"):
            return int(float(amount[:-1]) * 1_000)
        if amount.endswith("m"):
            return int(float(amount[:-1]) * 1_000_000)
        return int(amount)
    except (TypeError, ValueError):
        return None
