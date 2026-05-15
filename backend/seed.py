import os

from backend.models.election_model import add_candidate, create_election, set_election_active
from backend.models.user_model import create_user, find_user_by_email
from backend.services.audit_service import record_audit
from backend.services.security_service import hash_password
from backend.utils.db import get_connection, init_db, query_one

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "jacksonndirangu25@gmail.com")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Kihikoko")


def seed_sample_data() -> None:
    init_db()

    admin = find_user_by_email(ADMIN_EMAIL)
    if not admin:
        admin_id = create_user(
            "System Admin",
            ADMIN_EMAIL,
            hash_password(ADMIN_PASSWORD),
            "admin",
            "ADM-001",
            "ADM-001",
            "Election Administration",
        )
        record_audit("SEED_ADMIN_CREATED", admin_id)
    else:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET name = ?, password_hash = ?, role = ?, institution_id = ?, reg_number = ?, course = ?
                WHERE id = ?
                """,
                (
                    "System Admin",
                    hash_password(ADMIN_PASSWORD),
                    "admin",
                    "ADM-001",
                    "ADM-001",
                    "Election Administration",
                    admin["id"],
                ),
            )
        record_audit("SEED_ADMIN_UPDATED", admin["id"])

    student = find_user_by_email("student@school.edu")
    if not student:
        student_id = create_user(
            "Demo Student",
            "student@school.edu",
            hash_password("StudentPass123"),
            "student",
            "REG-2026-001",
            "REG-2026-001",
            "BSc Software Engineering",
        )
        record_audit("SEED_STUDENT_CREATED", student_id)

    existing = query_one("SELECT id FROM elections WHERE title = ?", ("Student Council Election 2026",))
    if not existing:
        election_id = create_election("Student Council Election 2026", "2026-05-01", "2026-05-10")
        add_candidate("Amina Otieno", election_id, "President", "Transparency, student welfare, and stronger academic support.")
        add_candidate("Brian Mwangi", election_id, "President", "Digital services, fair representation, and faster issue resolution.")
        add_candidate("Grace Wanjiku", election_id, "President", "Inclusive leadership, clubs funding, and safer campus spaces.")
        add_candidate("David Kariuki", election_id, "Finance", "Open budgets and monthly student finance reports.")
        add_candidate("Esther Njeri", election_id, "Finance", "Accountable spending and support for department projects.")
        add_candidate("Lilian Achieng", election_id, "Academics", "Better lecture feedback loops and exam preparation forums.")
        add_candidate("Samuel Kiptoo", election_id, "Academics", "Peer tutoring, timetable advocacy, and resource access.")
        set_election_active(election_id, True)
        record_audit("SEED_ELECTION_CREATED", None)
    else:
        election_id = existing["id"]
        for name, position in (
            ("David Kariuki", "Finance"),
            ("Esther Njeri", "Finance"),
            ("Lilian Achieng", "Academics"),
            ("Samuel Kiptoo", "Academics"),
        ):
            candidate = query_one(
                "SELECT id FROM candidates WHERE election_id = ? AND name = ? AND position = ?",
                (election_id, name, position),
            )
            if not candidate:
                add_candidate(name, election_id, position)


if __name__ == "__main__":
    seed_sample_data()
    print("Sample data ready.")
