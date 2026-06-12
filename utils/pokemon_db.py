import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["royal_bot"]

pokemon_collection = db["pokemon"]
pokemon_market = db["pokemon_market"]
pokemon_spawn_channels = db["pokemon_spawn_channels"]


# ─────────────────────────
# PLAYER DOCUMENT
# ─────────────────────────

def create_pokemon_profile(user_id):

    user = pokemon_collection.find_one({
        "user_id": str(user_id)
    })

    if not user:

        pokemon_collection.insert_one({

            "user_id": str(user_id),

            "pokemon": [],

            "team": []

        })


# ─────────────────────────
# GET PLAYER
# ─────────────────────────

def get_player(user_id):

    create_pokemon_profile(user_id)

    return pokemon_collection.find_one({

        "user_id": str(user_id)

    })


# ─────────────────────────
# OWNERSHIP
# ─────────────────────────

def owns_pokemon(user_id, pokemon_name):

    user = get_player(user_id)

    pokemon_name = pokemon_name.lower()

    for poke in user.get("pokemon", []):

        if poke["name"] == pokemon_name:

            return True

    return False


# ─────────────────────────
# ADD POKEMON
# ─────────────────────────

def add_pokemon(

    user_id,
    name,
    display,
    pokedex_id

):

    create_pokemon_profile(user_id)

    if owns_pokemon(user_id, name):

        return False

    pokemon_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$push": {

                "pokemon": {

                    "name": name.lower(),

                    "display": display,

                    "pokedex_id": pokedex_id,

                    "moves": []

                }

            }

        }

    )

    return True


# ─────────────────────────
# REMOVE POKEMON
# ─────────────────────────

def remove_pokemon(

    user_id,
    pokemon_name

):

    pokemon_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$pull": {

                "pokemon": {

                    "name": pokemon_name.lower()

                }

            }

        }

    )


# ─────────────────────────
# GET ALL POKEMON
# ─────────────────────────

def get_pokemon(user_id):

    user = get_player(user_id)

    return user.get(

        "pokemon",
        []

    )


# ─────────────────────────
# TEAM
# ─────────────────────────

def get_team(user_id):

    user = get_player(user_id)

    return user.get(

        "team",
        []

    )


def set_team(

    user_id,
    team

):

    pokemon_collection.update_one(

        {
            "user_id": str(user_id)
        },

        {
            "$set": {

                "team": team
            }
        }

    )


def remove_from_team(
    user_id,
    pokemon_name
):

    team = get_team(
        user_id
    )

    team = [

        p for p in team

        if p.lower() != pokemon_name.lower()
    ]

    set_team(
        user_id,
        team
    )


# ─────────────────────────
# MOVES
# ─────────────────────────

def set_moves(

    user_id,
    pokemon_name,
    moves

):

    pokemon_collection.update_one(

        {
            "user_id": str(user_id),

            "pokemon.name": pokemon_name.lower()

        },

        {
            "$set": {

                "pokemon.$.moves": moves

            }
        }

    )


def get_moves(

    user_id,
    pokemon_name

):

    user = get_player(user_id)

    for poke in user.get(

        "pokemon",
        []

    ):

        if poke["name"] == pokemon_name.lower():

            return poke.get(

                "moves",
                []

            )

    return []


# ─────────────────────────
# POKEMON DATA
# ─────────────────────────

def get_pokemon_data(
    user_id,
    pokemon_name
):

    user = get_player(
        user_id
    )

    for poke in user.get(
        "pokemon",
        []
    ):

        if poke["name"] == pokemon_name.lower():

            return poke

    return None


# ─────────────────────────
# TRANSFER
# ─────────────────────────

def transfer_pokemon(
    seller_id,
    buyer_id,
    pokemon_name
):

    seller = get_player(
        seller_id
    )

    pokemon_data = None

    for poke in seller["pokemon"]:

        if poke["name"] == pokemon_name.lower():

            pokemon_data = poke
            break

    if not pokemon_data:
        return False

    pokemon_collection.update_one(

        {
            "user_id": str(seller_id)
        },

        {
            "$pull": {

                "pokemon": {

                    "name": pokemon_name.lower()
                }
            }
        }
    )

    pokemon_collection.update_one(

        {
            "user_id": str(buyer_id)
        },

        {
            "$push": {

                "pokemon": pokemon_data
            }
        }
    )

    return True
