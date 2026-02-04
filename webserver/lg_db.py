import os
import json
from pathlib import Path
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool


# load project .env (optional) then compose .env and force override of OS env vars
load_dotenv(override=False)  # load local .env without overriding host env
_compose_env = Path(__file__).resolve().parents[1] / "my-postgres-compose" / ".env"
if _compose_env.exists():
    load_dotenv(_compose_env.as_posix(), override=True)  # force values from this file

# create a connection pool (uses .env or environment variables)
_CONNINFO = (
    f"postgresql://{os.getenv('LG_POSTGRES_USER','libregenie')}:"
    f"{os.getenv('LG_POSTGRES_PASSWORD','')}"
    f"@{os.getenv('LG_POSTGRES_HOST','db')}:{os.getenv('LG_POSTGRES_PORT','5432')}/"
    f"{os.getenv('LG_POSTGRES_DB','libredb')}"
)
_pool = ConnectionPool(conninfo=_CONNINFO, min_size=1, max_size=5)


def lg_hello_db() -> str:
    """
    Query SELECT * FROM hello and return results as a JSON string.
    """
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM hello;")
            rows = cur.fetchall()  # list of tuples
    # convert tuples to lists for JSON serialization
    return json.dumps([list(r) for r in rows])


def init_db():
    """Create necessary tables if they don't exist."""
    pk_type = "SERIAL PRIMARY KEY"
    json_type = "JSONB"
    
    queries = [
        f"""CREATE TABLE IF NOT EXISTS clients (
            client_id TEXT PRIMARY KEY,
            secret TEXT NOT NULL,
            xp_score INTEGER DEFAULT 0,
            tasks_completed_count INTEGER DEFAULT 0,
            objectives_completed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS client_objectives (
            id {pk_type},
            client_id TEXT REFERENCES clients(client_id),
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'not_started',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS client_tasks (
            id {pk_type},
            objective_id INTEGER REFERENCES client_objectives(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            weight INTEGER DEFAULT 1,
            is_completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS calendar_events (
            id {pk_type},
            client_id TEXT REFERENCES clients(client_id),
            title TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS chat_history (
            id {pk_type},
            client_id TEXT REFERENCES clients(client_id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS client_stats (
            client_id TEXT PRIMARY KEY REFERENCES clients(client_id),
            xp_score INTEGER DEFAULT 0,
            last_active TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS client_agenda (
            id {pk_type},
            client_id TEXT REFERENCES clients(client_id),
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            description TEXT,
            objective_id INTEGER
        )""",
        f"""CREATE TABLE IF NOT EXISTS client_completed_objectives (
            id {pk_type},
            client_id TEXT REFERENCES clients(client_id),
            data {json_type},
            score INTEGER,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS client_chat_history (
            id {pk_type},
            client_id TEXT REFERENCES clients(client_id),
            role TEXT,
            content {json_type},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS calendar_events (
            id {pk_type},
            client_id TEXT REFERENCES clients(client_id),
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )"""
    ]
    
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            for q in queries:
                cur.execute(q)
            
            # Simple migration for existing dev DB: try adding column
            try:
                cur.execute("ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS client_id TEXT REFERENCES clients(client_id);")
            except Exception:
                pass # Table might not exist or other error, handled by CREATE TABLE above


def register_device(client_id: str, secret: str) -> None:
    """Store the device uuid and secret pair."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clients (client_id, secret) 
                VALUES (%s, %s) 
                ON CONFLICT (client_id) 
                DO UPDATE SET secret = EXCLUDED.secret;
                """,
                (client_id, secret)
            )

def get_uuid_secret_count(uuid: str, secret: str) -> int:
    """Return the count of stored uuid-secret pairs."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clients WHERE client_id = %s AND secret = %s;", (uuid, secret))
            count = cur.fetchone()[0]
    return count

def get_client_stats(client_id: str) -> dict:
    """Retrieve XP score, tasks completed count, and objectives completed count."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT xp_score, tasks_completed_count, objectives_completed_count FROM clients WHERE client_id = %s;",
                (client_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "xp_score": row[0],
                    "tasks_completed_count": row[1],
                    "objectives_completed_count": row[2]
                }
            return {"xp_score": 0, "tasks_completed_count": 0, "objectives_completed_count": 0}

def get_client(client_id: str, secret: str) -> bool:
    """Check if client_id and secret match."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM clients WHERE client_id = %s AND secret = %s",
                (client_id, secret)
            )
            return cur.fetchone() is not None

def add_calendar_event(client_id: str, title: str, start_time: str, end_time: str) -> None:
    """Add a calendar event to the database."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO calendar_events (client_id, title, start_time, end_time) VALUES (%s, %s, %s, %s);",
                (client_id, title, start_time, end_time)
            )

def remove_calendar_event(client_id: str, title: str) -> None:
    """Remove a calendar event from the database."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM calendar_events WHERE client_id = %s AND title = %s;",
                (client_id, title)
            )

def get_all_events(client_id: str) -> list[dict]:
    """Retrieve all calendar events for a specific client."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT title, start_time, end_time FROM calendar_events WHERE client_id = %s;", (client_id,))
            rows = cur.fetchall()
            
    # Convert to list of dicts for frontend
    events = []
    for r in rows:
        events.append({
            "title": r[0],
            "start": r[1],
            "end": r[2]
        })
    return events

def add_chat_message(client_id: str, role: str, content: str) -> None:
    """Save a chat message to the history."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_history (client_id, role, content) VALUES (%s, %s, %s);",
                (client_id, role, content)
            )

def get_chat_history(client_id: str, limit: int = 50) -> list[dict]:
    """Retrieve chat history for a client."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM chat_history WHERE client_id = %s ORDER BY timestamp ASC LIMIT %s;",
                (client_id, limit)
            )
            rows = cur.fetchall()
            
    return [{"role": r[0], "content": r[1]} for r in rows]

def add_objective(client_id: str, title: str, description: str = "") -> int:
    """Add a new objective for a client and return its ID."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO client_objectives (client_id, title, description) VALUES (%s, %s, %s) RETURNING id;",
                (client_id, title, description)
            )
            return cur.fetchone()[0]

def add_task(objective_id: int, title: str, weight: int = 1) -> int:
    """Add a task to an objective and return its ID."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO client_tasks (objective_id, title, weight) VALUES (%s, %s, %s) RETURNING id;",
                (objective_id, title, weight)
            )
            return cur.fetchone()[0]

def get_client_objectives(client_id: str) -> list[dict]:
    """Retrieve all objectives and their tasks for a client."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            # Fetch objectives
            cur.execute("SELECT id, title, description, status FROM client_objectives WHERE client_id = %s ORDER BY created_at DESC;", (client_id,))
            objectives = []
            for row in cur.fetchall():
                obj_id, title, desc, status = row
                # Fetch tasks for each objective
                cur.execute("SELECT id, title, weight, is_completed FROM client_tasks WHERE objective_id = %s ORDER BY created_at ASC;", (obj_id,))
                tasks = [{"id": t[0], "title": t[1], "weight": t[2], "is_completed": t[3]} for t in cur.fetchall()]
                objectives.append({
                    "id": obj_id,
                    "title": title,
                    "description": desc,
                    "status": status,
                    "tasks": tasks
                })
            return objectives

def complete_task(client_id: str, task_id: int) -> bool:
    """Mark task as completed, update XP and counters. Returns True if successful."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            # Get task details and verify ownership
            cur.execute("""
                SELECT t.id, t.weight, t.is_completed, o.id 
                FROM client_tasks t
                JOIN client_objectives o ON t.objective_id = o.id
                WHERE t.id = %s AND o.client_id = %s
            """, (task_id, client_id))
            res = cur.fetchone()
            if not res or res[2]: # Not found or already completed
                return False
            
            weight, objective_id = res[1], res[3]

            # Mark complete
            cur.execute("UPDATE client_tasks SET is_completed = TRUE WHERE id = %s", (task_id,))
            
            # Update Client Stats
            cur.execute("""
                UPDATE clients 
                SET xp_score = xp_score + %s, tasks_completed_count = tasks_completed_count + 1 
                WHERE client_id = %s
            """, (weight, client_id))

            # Auto-update status to 'in_progress' if it was 'not_started'
            cur.execute("""
                UPDATE client_objectives SET status = 'in_progress' 
                WHERE id = %s AND status = 'not_started'
            """, (objective_id,))
            
            return True

def complete_objective(client_id: str, objective_id: int) -> bool:
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE client_objectives SET status = 'completed' 
                WHERE id = %s AND client_id = %s AND status != 'completed'
            """, (objective_id, client_id))
            
            if cur.rowcount > 0:
                cur.execute("UPDATE clients SET objectives_completed_count = objectives_completed_count + 1 WHERE client_id = %s", (client_id,))
                return True
            return False

def remove_objective(client_id: str, objective_id: int) -> None:
    """Remove an objective (and cascade delete tasks). Client ID check for security."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM client_objectives WHERE id = %s AND client_id = %s;",
                (objective_id, client_id)
            )

def remove_task(client_id: str, task_id: int) -> None:
    """Remove a specific task. Client ID check via join ensures ownership."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM client_tasks 
                   WHERE id = %s 
                   AND objective_id IN (SELECT id FROM client_objectives WHERE client_id = %s);""",
                (task_id, client_id)
            )
