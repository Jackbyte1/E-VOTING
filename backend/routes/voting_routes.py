from flask import Blueprint, request, session

from backend.models.election_model import get_active_election, get_all_elections, get_candidates_for_election
from backend.models.user_model import find_user_by_id
from backend.services.audit_service import record_audit
from backend.services.merkle_service import get_latest_merkle_root
from backend.services.vote_service import (
    cast_ballot,
    get_election_stats,
    get_results,
    get_user_voted_positions,
    has_user_voted,
    verify_vote_hash,
)
from backend.utils.db import query_one
from backend.utils.decorators import login_required
from backend.utils.responses import error, success

voting_bp = Blueprint("voting", __name__)


def _empty_stats() -> dict:
    return {
        "total_registered_voters": 0,
        "votes_cast": 0,
        "voters_cast": 0,
        "turnout_percentage": 0,
        "number_of_candidates": 0,
    }


@voting_bp.get("/election")
@login_required
def active_election():
    election = get_active_election()
    if not election:
        return success({"election": None, "candidates": []}, "No active election.")

    candidates = get_candidates_for_election(election["id"])
    voted_positions = sorted(get_user_voted_positions(session["user_id"], election["id"]))
    all_positions = sorted({candidate["position"] for candidate in candidates})
    return success(
        {
            "election": dict(election),
            "candidates": [dict(candidate) for candidate in candidates],
            "has_voted": len(voted_positions) == len(all_positions) if all_positions else has_user_voted(session["user_id"], election["id"]),
            "voted_positions": voted_positions,
        }
    )


@voting_bp.get("/elections")
@login_required
def list_elections():
    closed = []
    for election in get_all_elections():
        if not election["is_active"]:
            closed.append(
                {
                    "id": election["id"],
                    "title": election["title"],
                    "start_date": election["start_date"],
                    "end_date": election["end_date"],
                }
            )
    return success({"closed_elections": closed})


@voting_bp.post("/vote")
@login_required
def vote():
    data = request.get_json(silent=True) or {}
    election_id = data.get("election_id")
    selections = data.get("selections")
    candidate_id = data.get("candidate_id")
    user_id = session["user_id"]

    if session.get("role") != "student":
        return error("Only students can cast votes.", 403)
    if not election_id:
        return error("election_id is required.")
    if not selections and candidate_id:
        selections = [{"candidate_id": candidate_id}]
    if not selections:
        return error("At least one candidate selection is required.")

    election = query_one("SELECT * FROM elections WHERE id = ? AND is_active = 1", (election_id,))
    if not election:
        return error("Election is not active.", 400)

    try:
        receipts = cast_ballot(user_id, int(election_id), selections)
    except ValueError as exc:
        return error(str(exc), 409)

    positions = ",".join(receipt["position"] for receipt in receipts)
    record_audit(f"BALLOT_CAST:ELECTION:{election_id}:POSITIONS:{positions}", user_id)
    return success(
        {
            "vote_hash": receipts[0]["vote_hash"] if receipts else None,
            "vote_hashes": receipts,
        },
        "Vote submitted successfully.",
        201,
    )


@voting_bp.get("/results")
@login_required
def live_results():
    election_id = request.args.get("election_id", type=int)
    if not election_id:
        active = get_active_election()
        if not active:
            return success({"results": [], "stats": _empty_stats(), "merkle_root": None})
        election_id = int(active["id"])
    merkle_root = get_latest_merkle_root(election_id) if election_id else None
    return success({"results": get_results(election_id), "stats": get_election_stats(election_id), "merkle_root": merkle_root})


@voting_bp.get("/stats")
@login_required
def stats():
    election_id = request.args.get("election_id", type=int)
    if not election_id:
        active = get_active_election()
        if not active:
            return success({"stats": _empty_stats()})
        election_id = int(active["id"])
    return success({"stats": get_election_stats(election_id)})


@voting_bp.get("/verify-vote")
@login_required
def verify_vote():
    if session.get("role") != "student":
        return error("Only students can verify vote receipts.", 403)
    vote_hash = request.args.get("hash", "").strip()
    if not vote_hash:
        return error("hash query parameter is required.")
    return success({"verified": verify_vote_hash(vote_hash)})


@voting_bp.get("/profile")
@login_required
def profile():
    user = find_user_by_id(session["user_id"])
    if not user:
        return error("User not found.", 404)

    active = get_active_election()
    voting_status = "No active election"
    voted_positions = []
    if active:
        positions = {candidate["position"] for candidate in get_candidates_for_election(active["id"])}
        voted_positions = sorted(get_user_voted_positions(user["id"], active["id"]))
        voting_status = "Complete" if positions and len(voted_positions) == len(positions) else "Pending"

    return success(
        {
            "profile": {
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "institution_id": user["institution_id"],
                "reg_number": user["reg_number"],
                "course": user["course"],
                "voting_status": voting_status,
                "voted_positions": voted_positions,
            }
        }
    )
