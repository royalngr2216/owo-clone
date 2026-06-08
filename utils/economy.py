from pymongo import MongoClient
import os
import time

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["royal_bot"]

economy_collection = db["economy"]
history_collection = db["history"]


# CREATE ACCOUNT

def create_account(user_id):

    user_id = str(user_id)

    user = economy_collection.find_one({
        "user_id": user_id
    })

    if user:
        return

    economy_collection.insert_one({

        "user_id": user_id,

        "cash": 0,

        "daily": 0,
        "weekly": 0,
        "monthly": 0

    })


# CASH

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


# FORMAT CASH

def format_cash(amount):

    return f"${amount:,}"


# DAILY

def can_claim_daily(user_id):

    user = economy_collection.find_one({
        "user_id": str(user_id)
    })

    last_claim = user.get("daily", 0)

    return (
        time.time() - last_claim
    ) >= 86400


def update_daily(user_id):

    economy_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$set": {
                "daily": time.time()
            }
        }

    )


# WEEKLY

def can_claim_weekly(user_id):

    user = economy_collection.find_one({
        "user_id": str(user_id)
    })

    last_claim = user.get("weekly", 0)

    return (
        time.time() - last_claim
    ) >= 604800


def update_weekly(user_id):

    economy_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$set": {
                "weekly": time.time()
            }
        }

    )


# MONTHLY

def can_claim_monthly(user_id):

    user = economy_collection.find_one({
        "user_id": str(user_id)
    })

    last_claim = user.get("monthly", 0)

    return (
        time.time() - last_claim
    ) >= 2592000


def update_monthly(user_id):

    economy_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$set": {
                "monthly": time.time()
            }
        }

    )


# HISTORY

def add_history(
    user_id,
    game,
    result,
    amount,
    opponent
):

    history_collection.insert_one({

        "user_id": str(user_id),

        "game": game,

        "result": result,

        "amount": amount,

        "opponent": str(opponent),

        "time": time.time()

    })


def get_history(user_id):

    return list(

        history_collection.find({

            "user_id": str(user_id)

        })

        .sort("time", -1)

        .limit(10)

    )
