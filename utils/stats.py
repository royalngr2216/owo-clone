from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["royal_bot"]

stats_collection = db["player_stats"]


# CREATE PROFILE

def create_profile(user_id):

    user_id = str(user_id)

    user = stats_collection.find_one({
        "user_id": user_id
    })

    if user:
        return

    stats_collection.insert_one({

        "user_id": user_id,

        "wins": 0,
        "losses": 0,

        "total_won": 0,
        "total_lost": 0,

        "streak": 0,
        "best_streak": 0

    })


# WIN

def record_win(user_id, amount):

    create_profile(user_id)

    user = stats_collection.find_one({
        "user_id": str(user_id)
    })

    streak = user.get("streak", 0) + 1

    best = max(
        streak,
        user.get("best_streak", 0)
    )

    stats_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$inc": {

                "wins": 1,

                "total_won": amount

            },

            "$set": {

                "streak": streak,

                "best_streak": best

            }
        }

    )


# LOSS

def record_loss(user_id, amount):

    create_profile(user_id)

    stats_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$inc": {

                "losses": 1,

                "total_lost": amount

            },

            "$set": {

                "streak": 0

            }
        }

    )


# PROFILE

def get_profile(user_id):

    create_profile(user_id)

    user = stats_collection.find_one({
        "user_id": str(user_id)
    })

    wins = user.get("wins", 0)

    losses = user.get("losses", 0)

    matches = wins + losses

    winrate = 0

    if matches > 0:

        winrate = round(
            (wins / matches) * 100,
            2
        )

    return {

        "wins": wins,

        "losses": losses,

        "matches": matches,

        "winrate": winrate,

        "total_won": user.get(
            "total_won",
            0
        ),

        "total_lost": user.get(
            "total_lost",
            0
        ),

        "streak": user.get(
            "streak",
            0
        ),

        "best_streak": user.get(
            "best_streak",
            0
        )

    }
