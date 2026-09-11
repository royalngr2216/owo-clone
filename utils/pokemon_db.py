import os
from pymongo import MongoClient

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    format_cash,
    parse_amount
)

MONGO_URI = os.getenv("MONGO_URI")

if MONGO_URI:
    cluster = MongoClient(MONGO_URI)
    db = cluster["owo_clone"]
else:
    print("❌ WARNING: MONGO_URI not found in environment variables!")
    db = None

pokemon_collection = db["pokemon"] if db is not None else None
pokemon_market = db["pokemon_market"] if db is not None else None
pokemon_spawn_channels = db["pokemon_spawn_channels"] if db is not None else None
neel_log = db["neel_log"] if db is not None else None


def get_pokemon_data(user_id: int) -> dict:
    """Fetch a player's Pokémon document. Creates one if it doesn't exist."""
    user_data = pokemon_collection.find_one({"_id": user_id})
    if not user_data:
        user_data = {
            "_id": user_id,
            "team": [],
            "inventory": [],
            "caught_count": 0,
            "balls": {
                "pokeball": 0,
                "ultraball": 0,
                "masterball": 0
            }
        }
        pokemon_collection.insert_one(user_data)
    return user_data


def _normalize_pokemon_name(name: str) -> str:
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


def get_team(user_id: int) -> list:
    data = get_pokemon_data(user_id)
    return data.get("team", [])


def set_team(user_id: int, new_team: list):
    """Updates a user's equipped team."""
    pokemon_collection.update_one(
        {"_id": user_id},
        {"$set": {"team": new_team}},
        upsert=True
    )


def owns_pokemon(user_id: int, pokemon_name: str) -> bool:
    """Return True when the user already owns this Pokémon species."""
    data = get_pokemon_data(user_id)
    wanted = _normalize_pokemon_name(pokemon_name)
    return any(_normalize_pokemon_name(item) == wanted for item in data.get("inventory", []))


def add_pokemon(user_id: int, pokemon_name: str) -> bool:
    """Add a Pokémon only if the user does not already own that species."""
    if owns_pokemon(user_id, pokemon_name):
        return False
    pokemon_collection.update_one(
        {"_id": user_id},
        {"$addToSet": {"inventory": pokemon_name}, "$inc": {"caught_count": 1}},
        upsert=True
    )
    return True


def remove_from_team(user_id: int, pokemon_name: str):
    """Removes a specific Pokémon from the active team array."""
    pokemon_collection.update_one(
        {"_id": user_id},
        {"$pull": {"team": pokemon_name}}
    )


def get_balls(user_id):
    data = get_pokemon_data(user_id)
    if "balls" not in data:
        pokemon_collection.update_one(
            {"_id": user_id},
            {"$set": {"balls": {"pokeball": 0, "ultraball": 0, "masterball": 0}}}
        )
        return {"pokeball": 0, "ultraball": 0, "masterball": 0}
    return data["balls"]


def add_ball(user_id, ball_type, amount=1):
    pokemon_collection.update_one(
        {"_id": user_id},
        {"$inc": {f"balls.{ball_type}": amount}},
        upsert=True
    )


def remove_ball(user_id, ball_type, amount=1):
    pokemon_collection.update_one(
        {"_id": user_id},
        {"$inc": {f"balls.{ball_type}": -amount}}
    )


def log_neel_event(event_type: str, **fields):
    """Append an entry to the global Neel activity log."""
    import datetime as _dt
    entry = {"type": event_type, "timestamp": _dt.datetime.utcnow(), **fields}
    neel_log.insert_one(entry)


def get_neel_log(limit: int = 10) -> list:
    """Fetch the most recent Neel events, newest first."""
    return list(neel_log.find().sort("timestamp", -1).limit(limit))


def transfer_pokemon(seller_id: int, buyer_id: int, pokemon_name: str, price: int) -> tuple:
    """Handles the market logic for trading Pokémon."""
    if not owns_pokemon(seller_id, pokemon_name):
        return False, "The seller does not own this Pokémon."
    if owns_pokemon(buyer_id, pokemon_name):
        return False, "The buyer already owns this Pokémon."
    buyer_cash = get_cash(buyer_id)
    if buyer_cash < price:
        return False, "The buyer does not have enough cash."

    remove_cash(buyer_id, price)
    add_cash(seller_id, price)
    pokemon_collection.update_one({"_id": seller_id}, {"$pull": {"inventory": pokemon_name}})
    pokemon_collection.update_one({"_id": buyer_id}, {"$addToSet": {"inventory": pokemon_name}, "$inc": {"caught_count": 1}}, upsert=True)
    pokemon_collection.update_one({"_id": seller_id, "caught_count": {"$gt": 0}}, {"$inc": {"caught_count": -1}})
    return True, "Trade executed successfully!"
