from fastmcp import FastMCP
import os
import sqlite3

# Use a writable directory for the database.
# Precedence: DB_PATH env var → /tmp (always writable) → script dir as fallback
_DEFAULT_DB = os.path.join(
    os.environ.get("EXPENSE_DB_DIR", "/tmp"),
    "expenses.db"
)
DB_PATH = os.environ.get("DB_PATH", _DEFAULT_DB)

CATEGORIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categories.json")

mcp = FastMCP("ExpenseTracker")

def init_db():
    # Ensure the parent directory exists (important when DB_PATH is custom)
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS income(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                source TEXT NOT NULL,
                subsource TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        c.commit()

init_db()

# ───────────── EXPENSE TOOLS ─────────────

@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    with sqlite3.connect(DB_PATH, check_same_thread=False) as c:
        c.execute("PRAGMA journal_mode=WAL;")  # improves concurrent write safety
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, float(amount), category, subcategory, note)
        )
        c.commit()
        return {"status": "ok", "id": cur.lastrowid}

@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " GROUP BY category ORDER BY category ASC"
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def update_expense(id, date=None, amount=None, category=None, subcategory=None, note=None):
    '''
    Update an existing expense record by ID.
    Only the fields you provide will be updated; others remain unchanged.
    '''
    fields = {}
    if date        is not None: fields["date"]        = date
    if amount      is not None: fields["amount"]      = float(amount)
    if category    is not None: fields["category"]    = category
    if subcategory is not None: fields["subcategory"] = subcategory
    if note        is not None: fields["note"]        = note

    if not fields:
        return {"status": "error", "message": "No fields provided to update."}

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    params = list(fields.values()) + [id]

    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?",
            params
        )
        c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}."}
        return {"status": "ok", "updated_id": id, "updated_fields": list(fields.keys())}

@mcp.tool()
def delete_expense(id):
    '''Delete an expense record by ID.'''
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (id,))
        c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}."}
        return {"status": "ok", "deleted_id": id}

# ───────────── INCOME TOOLS ─────────────

@mcp.tool()
def add_income(date, amount, source, subsource="", note=""):
    '''Add a new income entry to the database.'''
    with sqlite3.connect(DB_PATH, check_same_thread=False) as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.execute(
            "INSERT INTO income(date, amount, source, subsource, note) VALUES (?,?,?,?,?)",
            (date, float(amount), source, subsource, note)
        )
        c.commit()
        return {"status": "ok", "id": cur.lastrowid}

@mcp.tool()
def list_income(start_date, end_date):
    '''List income entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, source, subsource, note
            FROM income
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize_income(start_date, end_date, source=None):
    '''Summarize income by source within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        query = """
            SELECT source, SUM(amount) AS total_amount
            FROM income
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " GROUP BY source ORDER BY source ASC"
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def update_income(id, date=None, amount=None, source=None, subsource=None, note=None):
    '''
    Update an existing income record by ID.
    Only the fields you provide will be updated; others remain unchanged.
    '''
    fields = {}
    if date      is not None: fields["date"]      = date
    if amount    is not None: fields["amount"]    = float(amount)
    if source    is not None: fields["source"]    = source
    if subsource is not None: fields["subsource"] = subsource
    if note      is not None: fields["note"]      = note

    if not fields:
        return {"status": "error", "message": "No fields provided to update."}

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    params = list(fields.values()) + [id]

    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.execute(
            f"UPDATE income SET {set_clause} WHERE id = ?",
            params
        )
        c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No income found with id {id}."}
        return {"status": "ok", "updated_id": id, "updated_fields": list(fields.keys())}

@mcp.tool()
def delete_income(id):
    '''Delete an income record by ID.'''
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.execute("DELETE FROM income WHERE id = ?", (id,))
        c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No income found with id {id}."}
        return {"status": "ok", "deleted_id": id}

@mcp.tool()
def net_savings(start_date, end_date):
    '''Calculate net savings (total income - total expenses) within a date range.'''
    with sqlite3.connect(DB_PATH) as c:
        income_cur = c.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM income WHERE date BETWEEN ? AND ?",
            (start_date, end_date)
        )
        total_income = income_cur.fetchone()[0]

        expense_cur = c.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date BETWEEN ? AND ?",
            (start_date, end_date)
        )
        total_expenses = expense_cur.fetchone()[0]

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": total_income - total_expenses
        }

# ───────────── RESOURCE ─────────────

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)