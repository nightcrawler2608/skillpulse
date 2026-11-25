"""Create (or reset) a limited database user for the public web app.

Why: the nightly pipeline needs full rights, but the website only needs to READ jobs and
skills and ADD anonymous feedback/usage rows. If the website's password ever leaked, this
user can't delete or change data.

    python -m skillpulse.db.app_role

- Uses the owner connection in DATABASE_URL to create role `skillpulse_app`.
- Makes a new random password (resets it if the role already exists).
- Writes APP_DATABASE_URL=... into your local .env. The password is never printed.
- Then copy APP_DATABASE_URL's value into the Hugging Face Space secret DATABASE_URL.
"""

from __future__ import annotations

import re
import secrets
from urllib.parse import quote, urlsplit, urlunsplit

from psycopg import sql

from skillpulse.config import PROJECT_ROOT, get_settings
from skillpulse.db.connection import get_connection

ROLE = "skillpulse_app"
WRITE_TABLES = ("feedback", "usage_events")


def app_url(owner_url: str, password: str) -> str:
    parts = urlsplit(owner_url)
    host = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit(parts._replace(netloc=f"{ROLE}:{quote(password, safe='')}@{host}"))


def save_to_env(url: str) -> None:
    env = PROJECT_ROOT / ".env"
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    line = f"APP_DATABASE_URL={url}"
    if re.search(r"(?m)^APP_DATABASE_URL=.*$", text):
        text = re.sub(r"(?m)^APP_DATABASE_URL=.*$", lambda _: line, text)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    env.write_text(text, encoding="utf-8")


def main() -> int:
    password = secrets.token_urlsafe(24)
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,)).fetchone()
        verb = "ALTER" if exists else "CREATE"
        conn.execute(sql.SQL(verb + " ROLE {} WITH LOGIN PASSWORD {}").format(
            sql.Identifier(ROLE), sql.Literal(password)))
        db = conn.info.dbname
        for stmt in [
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(db),
                                                                 sql.Identifier(ROLE)),
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(ROLE)),
            sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(
                sql.Identifier(ROLE)),
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}")
               .format(sql.Identifier(ROLE)),
            *[sql.SQL("GRANT INSERT ON {} TO {}").format(sql.Identifier(t), sql.Identifier(ROLE))
              for t in WRITE_TABLES],
            *[sql.SQL("GRANT USAGE ON SEQUENCE {} TO {}").format(sql.Identifier(f"{t}_id_seq"),
                                                                  sql.Identifier(ROLE))
              for t in WRITE_TABLES],
        ]:
            conn.execute(stmt)
        conn.commit()
    save_to_env(app_url(get_settings().database_url, password))
    print(f"{verb.lower()}d role {ROLE}: read-only, plus INSERT on {', '.join(WRITE_TABLES)}.")
    print("Saved APP_DATABASE_URL in your .env (password not shown here).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
