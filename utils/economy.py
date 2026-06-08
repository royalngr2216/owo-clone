import os
from pymongo import MongoClient
from datetime import datetime, timedelta

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["royal_bot"]

economy_collection = db["economy"]

STARTING_CASH = 1_000_000

─────────────────────────

ENSURE USER

─────────────────────────

def ensure_account(user_id):

user_id = str(user_id)

user = economy_collection.find_one({
    "user_id": user_id
})

if not user:

    economy_collection.insert_one({

        "user_id": user_id,

        "cash": STARTING_CASH,

        "daily_claimed": None,
        "weekly_claimed": None,
        "monthly_claimed": None,

        "history": []
    })

    user = economy_collection.find_one({
        "user_id": user_id
    })

return user

─────────────────────────

GET CASH

─────────────────────────

def get_cash(user_id):

user = ensure_account(user_id)

return user.get("cash", 0)

─────────────────────────

ADD CASH

─────────────────────────

def add_cash(user_id, amount):

ensure_account(user_id)

economy_collection.update_one(
    {"user_id": str(user_id)},
    {
        "$inc": {
            "cash": amount
        }
    }
)

─────────────────────────

REMOVE CASH

─────────────────────────

def remove_cash(user_id, amount):

ensure_account(user_id)

current = get_cash(user_id)

if current < amount:
    return False

economy_collection.update_one(
    {"user_id": str(user_id)},
    {
        "$inc": {
            "cash": -amount
        }
    }
)

return True

─────────────────────────

CAN AFFORD

─────────────────────────

def can_afford(user_id, amount):

return get_cash(user_id) >= amount

─────────────────────────

ADD HISTORY

─────────────────────────

def add_history(
user_id,
game,
result,
amount,
opponent_id
):

ensure_account(user_id)

entry = {

    "game": game,
    "result": result,
    "amount": amount,
    "opponent": str(opponent_id),
    "time": datetime.utcnow()
}

economy_collection.update_one(

    {"user_id": str(user_id)},

    {
        "$push": {
            "history": {
                "$each": [entry],
                "$position": 0,
                "$slice": 20
            }
        }
    }
)

─────────────────────────

FORMAT CASH

─────────────────────────

def format_cash(amount):

return f"${amount:,}"
