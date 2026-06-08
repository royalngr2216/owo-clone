from utils.economy import (
can_afford,
remove_cash,
add_cash
)

─────────────────────────

ACTIVE WAGERS

─────────────────────────

active_wagers = {}

─────────────────────────

CHECK ACTIVE

─────────────────────────

def in_wager(user_id):

return str(user_id) in active_wagers

─────────────────────────

CREATE WAGER

─────────────────────────

def create_wager(
user1_id,
user2_id,
amount,
game
):

# ALREADY IN GAME

if in_wager(user1_id):
    return (
        False,
        "You are already in a wager."
    )

if in_wager(user2_id):
    return (
        False,
        "Opponent is already in a wager."
    )

# ENOUGH MONEY

if not can_afford(
    user1_id,
    amount
):
    return (
        False,
        "You do not have enough cash."
    )

if not can_afford(
    user2_id,
    amount
):
    return (
        False,
        "Opponent does not have enough cash."
    )

# REMOVE MONEY

remove_cash(
    user1_id,
    amount
)

remove_cash(
    user2_id,
    amount
)

# LOCK USERS

active_wagers[str(user1_id)] = {

    "amount": amount,
    "game": game,
    "opponent": str(user2_id)
}

active_wagers[str(user2_id)] = {

    "amount": amount,
    "game": game,
    "opponent": str(user1_id)
}

return (
    True,
    "Wager created."
)

─────────────────────────

COMPLETE WAGER

─────────────────────────

def complete_wager(
winner_id,
loser_id,
amount
):

total = amount * 2

# 5% TAX

payout = int(total * 0.95)

add_cash(
    winner_id,
    payout
)

clear_wager(
    winner_id
)

clear_wager(
    loser_id
)

return payout

─────────────────────────

REFUND WAGER

─────────────────────────

def refund_wager(
user1_id,
user2_id,
amount
):

add_cash(
    user1_id,
    amount
)

add_cash(
    user2_id,
    amount
)

clear_wager(
    user1_id
)

clear_wager(
    user2_id
)

─────────────────────────

CLEAR WAGER

─────────────────────────

def clear_wager(user_id):

active_wagers.pop(
    str(user_id),
    None
)
