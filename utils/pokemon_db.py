from utils.economy import db

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

                    "name": name,

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
