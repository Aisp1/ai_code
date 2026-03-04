from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS datasource (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                dbType TEXT NOT NULL,
                host TEXT,
                port INTEGER,
                username TEXT,
                password TEXT,
                database_name TEXT,
                extraParams TEXT
            );

            CREATE TABLE IF NOT EXISTS sample (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL
            );
            """
        )


class InvokeRequest(BaseModel):
    cmd: str
    args: Dict[str, Any] = {}


class TaskLog(BaseModel):
    timestamp: float
    level: str
    content: str


class TaskState(BaseModel):
    finished: bool = False
    cancelled: bool = False
    logs: List[TaskLog] = Field(default_factory=list)
    result: Dict[str, Any] | None = None


TASKS: Dict[str, TaskState] = {}
TASK_LOCK = threading.Lock()

app = FastAPI(title="resource2code python backend")


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    if "database_name" in data:
        data["database"] = data.pop("database_name")
    return data


def cmd_get_all_ds(_: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM datasource ORDER BY name").fetchall()
    return [row_to_dict(r) for r in rows]


def cmd_create_ds(args: Dict[str, Any]) -> Any:
    ds = args["ds"]
    new_id = ds.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO datasource(id, name, dbType, host, port, username, password, database_name, extraParams)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                ds.get("name", ""),
                ds.get("dbType", ""),
                ds.get("host", ""),
                ds.get("port", 0),
                ds.get("username", ""),
                ds.get("password", ""),
                ds.get("database", ""),
                ds.get("extraParams", ""),
            ),
        )
    return new_id


def cmd_get_ds_by_id(args: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM datasource WHERE id = ?", (args["id"],)).fetchone()
    if not row:
        return None
    return row_to_dict(row)


def cmd_update_ds(args: Dict[str, Any]) -> Any:
    ds = args["ds"]
    with get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE datasource SET name=?, dbType=?, host=?, port=?, username=?, password=?, database_name=?, extraParams=?
            WHERE id=?
            """,
            (
                ds.get("name", ""),
                ds.get("dbType", ""),
                ds.get("host", ""),
                ds.get("port", 0),
                ds.get("username", ""),
                ds.get("password", ""),
                ds.get("database", ""),
                ds.get("extraParams", ""),
                ds.get("id"),
            ),
        )
    return cur.rowcount > 0


def cmd_delete_ds(args: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM datasource WHERE id=?", (args["id"],))
    return cur.rowcount > 0


def cmd_get_all_samples(_: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM sample ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def cmd_create_sample(args: Dict[str, Any]) -> Any:
    cs = args["cs"]
    new_id = cs.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute("INSERT INTO sample(id, name, content) VALUES (?, ?, ?)", (new_id, cs["name"], cs.get("content", "")))
    return new_id


def cmd_get_sample_by_id(args: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sample WHERE id=?", (args["id"],)).fetchone()
    return dict(row) if row else None


def cmd_update_sample(args: Dict[str, Any]) -> Any:
    cs = args["cs"]
    with get_conn() as conn:
        cur = conn.execute("UPDATE sample SET name=?, content=? WHERE id=?", (cs["name"], cs.get("content", ""), cs["id"]))
    return cur.rowcount > 0


def cmd_delete_sample(args: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM sample WHERE id=?", (args["id"],))
    return cur.rowcount > 0


def cmd_set_config(args: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (args["key"], args.get("value", "")),
        )
    return True


def cmd_get_config(args: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM config WHERE key=?", (args["key"],)).fetchone()
    return row["value"] if row else ""


def cmd_delete_config(args: Dict[str, Any]) -> Any:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM config WHERE key=?", (args["key"],))
    return cur.rowcount > 0


def cmd_get_file_system(args: Dict[str, Any]) -> Any:
    root = Path(args["path"]).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=400, detail="path not found or not a directory")

    def walk(path: Path, parent: str | None = None) -> Dict[str, Any]:
        node = {"id": str(path), "label": path.name, "isFolder": path.is_dir(), "children": []}
        if parent:
            node["parentId"] = parent
        if path.is_dir():
            children = []
            for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                children.append(walk(p, str(path)))
            node["children"] = children
        return node

    return [walk(root)]


def cmd_save_generated_file(args: Dict[str, Any]) -> Any:
    file = args["file"]
    path = Path(file["path"]).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(file.get("content", ""), encoding="utf-8")
    return True


def cmd_is_file_exsited(args: Dict[str, Any]) -> Any:
    return Path(args["filePath"]).expanduser().exists()


def _task_runner(task_id: str, request: Dict[str, Any]) -> None:
    def append(level: str, content: str) -> None:
        with TASK_LOCK:
            task = TASKS[task_id]
            task.logs.append(TaskLog(timestamp=time.time(), level=level, content=content))

    append("Info", "开始处理请求")
    time.sleep(0.5)
    if TASKS[task_id].cancelled:
        with TASK_LOCK:
            TASKS[task_id].finished = True
            TASKS[task_id].result = {"data": {"files": []}}
        return

    prompt = request.get("question", "")
    filename = "generated_example.py"
    content = f"# Auto-generated by Python backend\n# Prompt:\n# {prompt}\n\nprint('Hello from python backend')\n"
    append("Info", "已生成示例代码")

    with TASK_LOCK:
        TASKS[task_id].result = {"data": {"files": [{"name": filename, "path": filename, "content": content}]}}
        TASKS[task_id].finished = True
    append("Info", "任务完成")


def cmd_process_user_question(args: Dict[str, Any]) -> Any:
    request = args.get("request", {})
    task_id = str(uuid.uuid4())
    with TASK_LOCK:
        TASKS[task_id] = TaskState(finished=False, cancelled=False, logs=[], result=None)
    th = threading.Thread(target=_task_runner, args=(task_id, request), daemon=True)
    th.start()
    return task_id


def cmd_is_user_task_finished(args: Dict[str, Any]) -> Any:
    task = TASKS.get(args["taskId"])
    return bool(task and task.finished)


def cmd_get_user_task_logs(args: Dict[str, Any]) -> Any:
    task = TASKS.get(args["taskId"])
    if not task:
        return []
    return [l.model_dump() for l in task.logs]


def cmd_get_user_task_result(args: Dict[str, Any]) -> Any:
    task = TASKS.get(args["taskId"])
    return task.result if task else None


def cmd_cancel_user_task(args: Dict[str, Any]) -> Any:
    task = TASKS.get(args["taskId"])
    if task:
        task.cancelled = True
    return True


def cmd_get_tables(_: Dict[str, Any]) -> Any:
    return []


COMMANDS = {
    "get_all_ds": cmd_get_all_ds,
    "create_ds": cmd_create_ds,
    "get_ds_by_id": cmd_get_ds_by_id,
    "update_ds": cmd_update_ds,
    "delete_ds": cmd_delete_ds,
    "get_all_samples": cmd_get_all_samples,
    "create_sample": cmd_create_sample,
    "get_sample_by_id": cmd_get_sample_by_id,
    "update_sample": cmd_update_sample,
    "delete_sample": cmd_delete_sample,
    "set_config": cmd_set_config,
    "get_config": cmd_get_config,
    "delete_config": cmd_delete_config,
    "get_file_system": cmd_get_file_system,
    "save_generated_file": cmd_save_generated_file,
    "is_file_exsited": cmd_is_file_exsited,
    "process_user_question": cmd_process_user_question,
    "is_user_task_finished": cmd_is_user_task_finished,
    "get_user_task_logs": cmd_get_user_task_logs,
    "get_user_task_result": cmd_get_user_task_result,
    "cancel_user_task": cmd_cancel_user_task,
    "cancel_task": cmd_cancel_user_task,
    "get_tables": cmd_get_tables,
}


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/invoke")
def invoke(req: InvokeRequest) -> Any:
    handler = COMMANDS.get(req.cmd)
    if not handler:
        raise HTTPException(status_code=404, detail=f"unknown command: {req.cmd}")
    return handler(req.args)
