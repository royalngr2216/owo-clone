from datetime import datetime

from utils.economy import (
    economy_collection
)


# ─────────────────────────
# WORKER STATS
# ─────────────────────────

WORKER_LEVELS = {

    1: {
        "income": 100000,
        "storage": 100000
    },

    2: {
        "income": 125000,
        "storage": 125000
    },

    3: {
        "income": 150000,
        "storage": 150000
    },

    4: {
        "income": 200000,
        "storage": 200000
    },

    5: {
        "income": 250000,
        "storage": 250000
    }

}


# ─────────────────────────
# UPDATE WORKERS
# ─────────────────────────

def update_workers(user_id):

    user_data = economy_collection.find_one({

        "user_id": str(user_id)

    })


    if not user_data:

        return


    workers = user_data.get(
        "workers",
        {}
    )


    current_time = int(
        datetime.now().timestamp()
    )


    updated = False


    for worker_name, worker in workers.items():

        level = worker.get(
            "level",
            1
        )


        stored = worker.get(
            "stored",
            0
        )


        last_claim = worker.get(
            "last_claim",
            current_time
        )


        income = WORKER_LEVELS[level]["income"]

        storage_cap = WORKER_LEVELS[level]["storage"]


        # ALREADY FULL

        if stored >= storage_cap:

            continue


        elapsed = current_time - last_claim


        # MONEY PER SECOND

        generated = int(

            income * (elapsed / 86400)

        )


        if generated <= 0:

            continue


        new_stored = stored + generated


        # STORAGE LIMIT

        if new_stored > storage_cap:

            new_stored = storage_cap


        worker["stored"] = new_stored

        worker["last_claim"] = current_time

        updated = True


    if updated:

        economy_collection.update_one(

            {
                "user_id": str(user_id)
            },

            {
                "$set": {
                    "workers": workers
                }
            }
        )
