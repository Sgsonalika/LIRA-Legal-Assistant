"""backend/models.py"""
from flask_login import UserMixin
from backend.database import get_db
import hashlib

ROLES = [
    ("individual",  "Individual / General Public"),
    ("student",     "Law Student"),
    ("lawyer",      "Lawyer / Advocate"),
    ("paralegal",   "Paralegal"),
    ("business",    "Business Owner"),
    ("hr",          "HR Professional"),
    ("journalist",  "Journalist / Researcher"),
    ("ngo",         "NGO Worker"),
    ("government",  "Government Employee"),
    ("other",       "Other"),
]

class User(UserMixin):
    def __init__(self, row):
        self.id       = row["id"]
        self.name     = row["name"]
        self.email    = row["email"]
        self.password = row["password"]
        self.avatar   = row["avatar"]
        self.theme    = row["theme"]
        self.role     = row["role"] if "role" in row.keys() else "individual"

    def get_id(self): return str(self.id)

    def role_label(self):
        return next((l for k,l in ROLES if k == self.role), "Individual")

    @staticmethod
    def get_by_id(uid, db_path):
        conn = get_db(db_path)
        row  = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        conn.close()
        return User(row) if row else None

    @staticmethod
    def get_by_email(email, db_path):
        conn = get_db(db_path)
        row  = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        return User(row) if row else None

    @staticmethod
    def create(name, email, password_hash, db_path):
        conn = get_db(db_path)
        try:
            conn.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                         (name, email, password_hash))
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            return User(row)
        finally:
            conn.close()

    def update_theme(self, theme, db_path):
        conn = get_db(db_path)
        conn.execute("UPDATE users SET theme=? WHERE id=?", (theme, self.id))
        conn.commit(); conn.close(); self.theme = theme

    def update_name(self, name, db_path):
        conn = get_db(db_path)
        conn.execute("UPDATE users SET name=? WHERE id=?", (name, self.id))
        conn.commit(); conn.close(); self.name = name

    def update_role(self, role, db_path):
        conn = get_db(db_path)
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, self.id))
        conn.commit(); conn.close(); self.role = role

    @staticmethod
    def hash_password(pw):
        try:
            from flask_bcrypt import generate_password_hash
            return generate_password_hash(pw).decode("utf-8")
        except Exception:
            return hashlib.sha256(pw.encode()).hexdigest()

    @staticmethod
    def check_password(pw, hashed):
        try:
            from flask_bcrypt import check_password_hash
            return check_password_hash(hashed, pw)
        except Exception:
            return hashlib.sha256(pw.encode()).hexdigest() == hashed
