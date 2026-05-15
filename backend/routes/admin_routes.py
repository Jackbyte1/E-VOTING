import csv
import io

from flask import Blueprint, Response, request, session

from backend.models.election_model import (
    add_candidate,
    create_election,
    get_active_election,
    get_all_elections,
    get_candidates_for_election,
    get_election,
    set_election_active,
)
from backend.models.user_model import list_users, update_user_role
from backend.services.audit_service import record_audit
from backend.services.integrity_service import verify_system_integrity
from backend.services.merkle_service import compute_and_store_election_merkle_root, get_latest_merkle_root, get_latest_merkle_root_any
from backend.services.vote_service import get_election_stats, get_results
from backend.utils.db import query_all
from backend.utils.decorators import admin_required
from backend.utils.responses import error, success

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _empty_stats() -> dict:
    return {
        "total_registered_voters": 0,
        "votes_cast": 0,
        "voters_cast": 0,
        "turnout_percentage": 0,
        "number_of_candidates": 0,
    }


def _active_or_requested_election_id():
    election_id = request.args.get("election_id", type=int)
    if election_id:
        return election_id
    active_election = get_active_election()
    return int(active_election["id"]) if active_election else None


@admin_bp.get("/elections")
@admin_required
def elections():
    data = []
    for election in get_all_elections():
        item = dict(election)
        item["candidates"] = [dict(candidate) for candidate in get_candidates_for_election(election["id"])]
        data.append(item)
    return success({"elections": data})


@admin_bp.post("/create-election")
@admin_required
def create_election_route():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    start_date = data.get("start_date", "").strip()
    end_date = data.get("end_date", "").strip()

    if not title or not start_date or not end_date:
        return error("title, start_date, and end_date are required.")
    if get_active_election():
        return error("Election setup is locked while an election is open. Close the active election before creating another one.", 409)

    election_id = create_election(title, start_date, end_date, session["user_id"])
    record_audit(f"CREATE_ELECTION:{election_id}:{title}", session["user_id"])
    return success({"election_id": election_id}, "Election created.", 201)


@admin_bp.post("/add-candidate")
@admin_required
def add_candidate_route():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    position = data.get("position", "").strip()
    election_id = data.get("election_id")
    allowed_positions = {"President", "Finance", "Academics"}

    if not name or not position or not election_id:
        return error("name, position, and election_id are required.")
    if position not in allowed_positions:
        return error("Position must be President, Finance, or Academics.")
    election = get_election(election_id)
    if not election:
        return error("Election not found.", 404)
    if get_active_election():
        return error("Candidate setup is locked while an election is open. Close the active election before adding candidates.", 409)
    if election["is_active"]:
        return error("Candidates can only be added before an election is opened.", 409)

    candidate_id = add_candidate(name, int(election_id), position, None)
    record_audit(f"ADD_CANDIDATE:{candidate_id}:ELECTION:{election_id}", session["user_id"])
    return success({"candidate_id": candidate_id}, "Candidate added.", 201)


@admin_bp.post("/open-election")
@admin_required
def open_election():
    data = request.get_json(silent=True) or {}
    election_id = data.get("election_id")
    if not election_id:
        return error("election_id is required.")
    if not get_election(election_id):
        return error("Election not found.", 404)
    active_election = get_active_election()
    if active_election and int(active_election["id"]) != int(election_id):
        return error("Another election is already open. Close it before opening a different election.", 409)

    set_election_active(int(election_id), True)
    record_audit(f"OPEN_ELECTION:{election_id}", session["user_id"])
    return success(message="Election opened.")


@admin_bp.post("/close-election")
@admin_required
def close_election():
    data = request.get_json(silent=True) or {}
    election_id = data.get("election_id")
    if not election_id:
        return error("election_id is required.")
    if not get_election(election_id):
        return error("Election not found.", 404)

    set_election_active(int(election_id), False)
    merkle_root = compute_and_store_election_merkle_root(int(election_id))
    record_audit(f"CLOSE_ELECTION:{election_id}:MERKLE_ROOT_PUBLISHED", session["user_id"], merkle_root)
    return success({"merkle_root": merkle_root}, "Election closed.")


@admin_bp.get("/results")
@admin_required
def results():
    election_id = _active_or_requested_election_id()
    if not election_id:
        return success({"results": [], "stats": _empty_stats(), "merkle_root": None})
    merkle_root = get_latest_merkle_root(election_id) if election_id else get_latest_merkle_root_any()
    return success({"results": get_results(election_id), "stats": get_election_stats(election_id), "merkle_root": merkle_root})


@admin_bp.get("/stats")
@admin_required
def stats():
    election_id = _active_or_requested_election_id()
    if not election_id:
        return success({"stats": _empty_stats()})
    return success({"stats": get_election_stats(election_id)})


@admin_bp.get("/audit-logs")
@admin_required
def audit_logs():
    logs = query_all("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200")
    return success({"audit_logs": [dict(log) for log in logs]})


@admin_bp.get("/integrity")
@admin_required
def integrity():
    election_id = _active_or_requested_election_id()
    return success({"integrity": verify_system_integrity(election_id)})


@admin_bp.get("/users")
@admin_required
def users():
    return success({"users": [dict(user) for user in list_users()]})


@admin_bp.post("/update-user-role")
@admin_required
def update_role():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    role = data.get("role", "").strip().lower()
    if not user_id or role not in {"student", "admin"}:
        return error("user_id and a valid role are required.")
    if int(user_id) == session["user_id"] and role != "admin":
        return error("You cannot remove your own admin role.", 400)
    update_user_role(int(user_id), role)
    record_audit(f"UPDATE_USER_ROLE:{user_id}:{role}", session["user_id"])
    return success(message="User role updated.")


@admin_bp.get("/export-report")
@admin_required
def export_report():
    election_id = _active_or_requested_election_id()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Election", "Position", "Candidate", "Votes", "Total Position Votes", "Percentage"])
    rows = get_results(election_id) if election_id else []
    for row in rows:
        writer.writerow(
            [
                row["election_title"],
                row["position"],
                row["candidate_name"],
                row["vote_count"],
                row["total_votes"],
                row["percentage"],
            ]
        )
    stats = get_election_stats(election_id) if election_id else _empty_stats()
    writer.writerow([])
    writer.writerow(["Total Registered Voters", stats["total_registered_voters"]])
    writer.writerow(["Votes Cast", stats["votes_cast"]])
    writer.writerow(["Turnout", f'{stats["turnout_percentage"]}%'])
    writer.writerow(["Candidates", stats["number_of_candidates"]])
    if election_id:
        merkle = get_latest_merkle_root(election_id)
        writer.writerow(["Merkle Root", merkle["merkle_root"] if merkle else "Not published"])

    record_audit(f"EXPORT_REPORT:ELECTION:{election_id or 'ALL'}", session["user_id"])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=election-report.csv"},
    )
