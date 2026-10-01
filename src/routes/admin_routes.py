from fastapi import Body
from fastapi import APIRouter, Request, Form, UploadFile, File, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import sqlite3
import io
import csv
import secrets
import re
import config.settings as config
from src.db_session import get_session
from src.services.word_manager import WordManager
from src.db_session import get_db_path

router = APIRouter()
templates = Jinja2Templates(directory=config.templates)

security = HTTPBasic()

DB_PATH = get_db_path()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_username or not admin_password:
        # Fail closed: with no credentials configured, deny access instead
        # of falling back to a default/blank password.
        raise HTTPException(status_code=401, detail="Admin credentials not configured", headers={"WWW-Authenticate": "Basic"})
    correct_username = secrets.compare_digest(credentials.username, admin_username)
    correct_password = secrets.compare_digest(credentials.password, admin_password)
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _table(conn, name: str) -> str:
    """Return `name` only if it is a real user table (blocks SQL injection
    through the table_name path parameter)."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=? AND name NOT LIKE 'sqlite_%'",
        (name,),
    ).fetchone()
    if not row or not _IDENT.match(row[0]):
        raise HTTPException(status_code=404, detail="Unknown table")
    return row[0]


def _columns(conn, table: str) -> list:
    return [c[1] for c in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def _check_cols(conn, table: str, cols) -> None:
    valid = set(_columns(conn, table))
    bad = [c for c in cols if c not in valid]
    if bad:
        raise HTTPException(status_code=400, detail="Unknown column(s)")


@router.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request, creds: HTTPBasicCredentials = Depends(authenticate)):    
    print("database using in admin:", DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall() if row[0] != "sqlite_sequence"]
    return templates.TemplateResponse("admin_home.html", {"request": request, "tables": tables})

@router.get("/admin/logout", response_class=HTMLResponse)
async def logout():
    response = RedirectResponse(url="/admin")
    response.headers["WWW-Authenticate"] = 'Basic realm="logout"'
    response.status_code = 401
    return response

@router.get("/admin/table/{table_name}", response_class=HTMLResponse)
async def view_table(request: Request, table_name: str, search: str = "", page: int = 1, creds: HTTPBasicCredentials = Depends(authenticate)):
    limit = 200
    page = max(page, 1)
    offset = (page - 1) * limit

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        table_name = _table(conn, table_name)
        columns = _columns(conn, table_name)

        if search:
            conditions = [f'"{col}" LIKE ?' for col in columns]
            where = " OR ".join(conditions)
            sql = f'SELECT rowid, * FROM "{table_name}" WHERE {where} LIMIT ? OFFSET ?'
            values = [f"%{search}%"] * len(conditions) + [limit, offset]
            c.execute(sql, values)
            c_total = conn.cursor()
            c_total.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE {where}', [f"%{search}%"] * len(conditions))
        else:
            c.execute(f'SELECT rowid, * FROM "{table_name}" LIMIT ? OFFSET ?', (limit, offset))
            c_total = conn.cursor()
            c_total.execute(f'SELECT COUNT(*) FROM "{table_name}"')

        records = c.fetchall()
        total_records = c_total.fetchone()[0]
        total_pages = (total_records + limit - 1) // limit

    return templates.TemplateResponse("admin_table.html", {
        "request": request,
        "table_name": table_name,
        "columns": ["rowid"] + columns,
        "records": records,
        "search": search,
        "page": page,
        "total_pages": total_pages
    })

@router.post("/admin/table/{table_name}/delete")
async def delete_row(table_name: str, rowid: int = Form(...), creds: HTTPBasicCredentials = Depends(authenticate)):
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")  # Ensure foreign key constraints are enforced
        c = conn.cursor()
        table_name = _table(conn, table_name)
        c.execute(f'DELETE FROM "{table_name}" WHERE rowid=?', (rowid,))
        conn.commit()
    return RedirectResponse(url=f"/admin/table/{table_name}", status_code=303)

@router.post("/admin/table/{table_name}/add")
async def add_row(table_name: str, request: Request, creds: HTTPBasicCredentials = Depends(authenticate)):
    form = await request.form()
    fields = [key for key in form.keys() if key != "table_name"]
    values = [form[key] for key in fields]

    placeholders = ", ".join("?" for _ in fields)
    columns = ", ".join(f'"{f}"' for f in fields)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        table_name = _table(conn, table_name)
        _check_cols(conn, table_name, fields)
        c.execute(f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})', values)
        conn.commit()

    return RedirectResponse(url=f"/admin/table/{table_name}", status_code=303)

@router.post("/admin/table/{table_name}/edit")
async def edit_row(table_name: str, request: Request, creds: HTTPBasicCredentials = Depends(authenticate)):
    form = await request.form()
    rowid = form.get("rowid")
    fields = [key for key in form.keys() if key not in ("table_name", "rowid")]
    updates = [f'"{field}" = ?' for field in fields]
    values = [form[field] for field in fields]
    values.append(rowid)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        table_name = _table(conn, table_name)
        _check_cols(conn, table_name, fields)
        sql = f'UPDATE "{table_name}" SET {", ".join(updates)} WHERE rowid = ?'
        c.execute(sql, values)
        conn.commit()

    return RedirectResponse(url=f"/admin/table/{table_name}", status_code=303)

@router.get("/admin/table/{table_name}/export")
async def export_csv(table_name: str, creds: HTTPBasicCredentials = Depends(authenticate)):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        table_name = _table(conn, table_name)
        c.execute(f'SELECT * FROM "{table_name}"')
        rows = c.fetchall()
        headers = _columns(conn, table_name)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={table_name}.csv"
    })

@router.post("/admin/table/{table_name}/import")
async def import_csv(table_name: str, file: UploadFile = File(...), creds: HTTPBasicCredentials = Depends(authenticate)):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    content = content.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    headers = rows[0]
    data_rows = rows[1:]

    placeholders = ", ".join("?" for _ in headers)
    columns = ", ".join(f'"{h}"' for h in headers)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        table_name = _table(conn, table_name)
        _check_cols(conn, table_name, headers)
        for row in data_rows:
            c.execute(f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})', row)
        conn.commit()

    return RedirectResponse(url=f"/admin/table/{table_name}", status_code=303)

@router.get("/admin/importwords", response_class=HTMLResponse)
async def import_words_form(request: Request, creds: HTTPBasicCredentials = Depends(authenticate)):
    return templates.TemplateResponse("import_words.html", {"request": request})

@router.post("/admin/importwords", response_class=HTMLResponse)
async def import_words_json(
    request: Request,
    file: UploadFile = File(...),
    creds: HTTPBasicCredentials = Depends(authenticate)
):
    with get_session() as session:
        word_manager = WordManager(session)
        count = word_manager.import_words_from_json(file.file)
    message = f"Imported {count} unique words from JSON."
    return templates.TemplateResponse("import_words.html", {"request": request, "message": message})

# Route to add a column to a table
@router.post("/admin/table/{table_name}/add_column")
async def add_column(
    table_name: str,
    column_name: str = Form(...),
    column_type: str = Form(...),
    creds: HTTPBasicCredentials = Depends(authenticate)
):
    # Only allow valid SQLite types for safety
    valid_types = {"INTEGER", "TEXT", "REAL", "BLOB"}
    if column_type.upper() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid column type. Must be one of {valid_types}")
    if not _IDENT.match(column_name):
        raise HTTPException(status_code=400, detail="Invalid column name")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        table_name = _table(conn, table_name)
        try:
            c.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column_type.upper()}')
            conn.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "message": f"Column '{column_name}' added to '{table_name}'"}

# Route to delete a column from a table (SQLite does not support DROP COLUMN directly)
@router.post("/admin/table/{table_name}/delete_column")
async def delete_column(
    table_name: str,
    column_name: str = Form(...),
    creds: HTTPBasicCredentials = Depends(authenticate)
):
    # SQLite does not support DROP COLUMN directly; workaround is to recreate the table
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        table_name = _table(conn, table_name)
        if not _IDENT.match(column_name):
            raise HTTPException(status_code=400, detail="Invalid column name")
        # Get current columns
        c.execute(f'PRAGMA table_info("{table_name}")')
        columns_info = c.fetchall()
        columns = [col[1] for col in columns_info if col[1] != column_name]
        if len(columns) == len(columns_info):
            raise HTTPException(status_code=400, detail=f"Column '{column_name}' not found in '{table_name}'")
        columns_str = ", ".join(columns)
        # Start transaction
        try:
            c.execute("BEGIN TRANSACTION;")
            # Rename old table
            c.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_old;")
            # Get CREATE statement for old table
            c.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}_old';")
            create_sql = c.fetchone()[0]
            # Remove the column from CREATE statement
            import re
            pattern = re.compile(rf",?\s*\"?{re.escape(column_name)}\"? [^,)]*")
            new_create_sql = pattern.sub("", create_sql)
            new_create_sql = new_create_sql.replace(f"{table_name}_old", table_name)
            c.execute(new_create_sql)
            # Copy data
            c.execute(f"INSERT INTO {table_name} ({columns_str}) SELECT {columns_str} FROM {table_name}_old;")
            # Drop old table
            c.execute(f"DROP TABLE {table_name}_old;")
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "message": f"Column '{column_name}' deleted from '{table_name}'"}


@router.post("/admin/users/{name}/password")
async def admin_set_password(name: str, password: str = Form(..., min_length=4, max_length=128),
                             creds: HTTPBasicCredentials = Depends(authenticate)):
    """Operator reset, e.g. for legacy passwordless accounts that can no
    longer log in (only GUEST may be passwordless)."""
    from sqlmodel import select
    from sqlalchemy import func
    from src.models.user import User
    from src.security import hash_password

    with get_session() as session:
        user = session.exec(select(User).where(func.upper(User.name) == name.upper())).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.password = hash_password(password)
        session.add(user)
        session.commit()
    return {"status": "success"}
