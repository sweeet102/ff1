import os
import sys
import json
import csv
import shutil
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO
from contextlib import contextmanager, asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "inventory.db"
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"
BACKUPS_DIR = BASE_DIR / "backups"
STATIC_DIR = BASE_DIR / "static"

for d in [UPLOADS_DIR, EXPORTS_DIR, BACKUPS_DIR]:
    d.mkdir(exist_ok=True)


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT DEFAULT '📦',
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER DEFAULT NULL,
                purchase_date TEXT NOT NULL,
                price REAL NOT NULL,
                expected_lifespan_months INTEGER DEFAULT NULL,
                status TEXT DEFAULT '在用',
                disposal_date TEXT DEFAULT NULL,
                warranty_months INTEGER DEFAULT NULL,
                notes TEXT DEFAULT '',
                photo_path TEXT DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            );
        """)

        # seed default categories if empty
        if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            defaults = [
                ("电子产品", "💻", 1),
                ("衣物鞋帽", "👕", 2),
                ("日用品", "🏠", 3),
                ("食品饮料", "🍜", 4),
                ("图书文具", "📚", 5),
                ("其他", "📦", 99),
            ]
            db.executemany(
                "INSERT INTO categories (name, icon, sort_order) VALUES (?,?,?)",
                defaults,
            )


@asynccontextmanager
async def lifespan(app):
    init_db()
    auto_backup()
    yield


app = FastAPI(title="物品仓库", lifespan=lifespan)


# ── helpers ──────────────────────────────────────────────

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def compute_item_stats(item: dict) -> dict:
    buy_date = datetime.strptime(item["purchase_date"], "%Y-%m-%d")
    today = datetime.today()
    held_days = (today - buy_date).days

    if item["status"] == "在用":
        end_date = today
    elif item["disposal_date"]:
        end_date = datetime.strptime(item["disposal_date"], "%Y-%m-%d")
    else:
        end_date = today

    actual_days = max((end_date - buy_date).days, 1)
    cost_per_day = round(item["price"] / actual_days, 2)

    expected_cost_per_day = None
    if item.get("expected_lifespan_months"):
        lifespan_days = item["expected_lifespan_months"] * 30
        expected_cost_per_day = round(item["price"] / lifespan_days, 2)

    warranty_remaining = None
    if item.get("warranty_months"):
        warranty_end = buy_date + timedelta(days=item["warranty_months"] * 30)
        remaining = (warranty_end - today).days
        warranty_remaining = max(remaining, 0)

    return {
        **item,
        "held_days": held_days,
        "cost_per_day": cost_per_day,
        "expected_cost_per_day": expected_cost_per_day,
        "warranty_remaining_days": warranty_remaining,
    }


# ── categories ───────────────────────────────────────────

@app.get("/api/categories")
def list_categories():
    with get_db() as db:
        rows = db.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/api/categories")
def create_category(data: dict):
    with get_db() as db:
        try:
            cur = db.execute(
                "INSERT INTO categories (name, icon) VALUES (?,?)",
                (data["name"], data.get("icon", "📦")),
            )
            return {"id": cur.lastrowid}
        except sqlite3.IntegrityError:
            raise HTTPException(400, "分类名已存在")


@app.put("/api/categories/{cat_id}")
def update_category(cat_id: int, data: dict):
    with get_db() as db:
        db.execute(
            "UPDATE categories SET name=?, icon=? WHERE id=?",
            (data.get("name"), data.get("icon"), cat_id),
        )
    return {"ok": True}


@app.delete("/api/categories/{cat_id}")
def delete_category(cat_id: int):
    with get_db() as db:
        db.execute("UPDATE items SET category_id=NULL WHERE category_id=?", (cat_id,))
        db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    return {"ok": True}


# ── items ────────────────────────────────────────────────

@app.get("/api/items")
def list_items(
    search: str = Query(default=""),
    category_id: int = Query(default=None),
    status: str = Query(default=""),
):
    sql = "SELECT * FROM items WHERE 1=1"
    params = []
    if search:
        sql += " AND name LIKE ?"
        params.append(f"%{search}%")
    if category_id:
        sql += " AND category_id = ?"
        params.append(category_id)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY purchase_date DESC"

    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
    return [compute_item_stats(row_to_dict(r)) for r in rows]


@app.get("/api/items/{item_id}")
def get_item(item_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(404, "物品不存在")
    return compute_item_stats(row_to_dict(row))


@app.post("/api/items")
def create_item(data: dict):
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO items
               (name, category_id, purchase_date, price,
                expected_lifespan_months, status, disposal_date,
                warranty_months, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                data["name"],
                data.get("category_id"),
                data["purchase_date"],
                data["price"],
                data.get("expected_lifespan_months"),
                data.get("status", "在用"),
                data.get("disposal_date"),
                data.get("warranty_months"),
                data.get("notes", ""),
            ),
        )
        return {"id": cur.lastrowid}


@app.put("/api/items/{item_id}")
def update_item(item_id: int, data: dict):
    with get_db() as db:
        db.execute(
            """UPDATE items SET
               name=?, category_id=?, purchase_date=?, price=?,
               expected_lifespan_months=?, status=?, disposal_date=?,
               warranty_months=?, notes=?,
               updated_at=datetime('now','localtime')
               WHERE id=?""",
            (
                data["name"],
                data.get("category_id"),
                data["purchase_date"],
                data["price"],
                data.get("expected_lifespan_months"),
                data.get("status", "在用"),
                data.get("disposal_date"),
                data.get("warranty_months"),
                data.get("notes", ""),
                item_id,
            ),
        )
    return {"ok": True}


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    with get_db() as db:
        item = db.execute("SELECT photo_path FROM items WHERE id=?", (item_id,)).fetchone()
        if item and item["photo_path"]:
            p = Path(item["photo_path"])
            if p.exists():
                p.unlink()
        db.execute("DELETE FROM items WHERE id=?", (item_id,))
    return {"ok": True}


# ── photos ───────────────────────────────────────────────

@app.post("/api/items/{item_id}/photo")
def upload_photo(item_id: int, file: UploadFile = File(...)):
    ext = Path(file.filename).suffix or ".jpg"
    safe_name = f"item_{item_id}_{hashlib.md5(file.filename.encode()).hexdigest()[:8]}{ext}"
    dest = UPLOADS_DIR / safe_name

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    with get_db() as db:
        db.execute("UPDATE items SET photo_path=? WHERE id=?", (str(dest), item_id))
    return {"photo_path": str(dest)}


@app.get("/api/items/{item_id}/photo")
def get_photo(item_id: int):
    with get_db() as db:
        row = db.execute("SELECT photo_path FROM items WHERE id=?", (item_id,)).fetchone()
    if not row or not row["photo_path"]:
        raise HTTPException(404, "没有照片")
    return FileResponse(row["photo_path"])


# ── image search ─────────────────────────────────────────

@app.get("/api/images/search")
def search_images(q: str = Query(default="")):
    """Search for product images via DuckDuckGo (no API key needed)."""
    import urllib.request
    import urllib.parse

    results = []
    try:
        encoded = urllib.parse.quote(q)
        url = f"https://duckduckgo.com/?q={encoded}&t=h_&iar=images&iax=images&ia=images"
        # Use a lightweight approach - return search URL and a note
        # In practice, scraping would need a headless browser.
        # For now, we provide a helpful fallback.
        results.append({
            "url": f"https://source.unsplash.com/400x400/?{encoded}",
            "thumb": f"https://source.unsplash.com/200x200/?{encoded}",
            "source": "Unsplash",
        })
    except Exception:
        pass
    return results


# ── statistics ───────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    with get_db() as db:
        items = [row_to_dict(r) for r in db.execute("SELECT * FROM items").fetchall()]
        cats = [row_to_dict(r) for r in db.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()]

    items = [compute_item_stats(i) for i in items]

    total_spent = sum(i["price"] for i in items)
    active_items = [i for i in items if i["status"] == "在用"]
    active_value = sum(i["price"] for i in active_items)
    disposed = [i for i in items if i["status"] != "在用"]

    # by category
    cat_spending = {}
    for i in items:
        cid = i.get("category_id")
        name = next((c["name"] for c in cats if c["id"] == cid), "未分类")
        cat_spending[name] = cat_spending.get(name, 0) + i["price"]
    cat_pie = [{"name": k, "value": round(v, 2)} for k, v in cat_spending.items()]

    # monthly spending
    monthly = {}
    for i in items:
        month = i["purchase_date"][:7]
        monthly[month] = monthly.get(month, 0) + i["price"]
    monthly_trend = [{"month": k, "value": round(v, 2)} for k, v in sorted(monthly.items())]

    # yearly spending
    yearly = {}
    for i in items:
        year = i["purchase_date"][:4]
        yearly[year] = yearly.get(year, 0) + i["price"]
    yearly_trend = [{"year": k, "value": round(v, 2)} for k, v in sorted(yearly.items())]

    # top cost per day
    top_cost = sorted(items, key=lambda x: x["cost_per_day"], reverse=True)[:10]
    top_cost_list = [
        {"name": i["name"], "cost_per_day": i["cost_per_day"], "price": i["price"]}
        for i in top_cost
    ]

    # warranty alerts
    today = datetime.today()
    warranty_alerts = []
    for i in items:
        if i.get("warranty_remaining_days") is not None and i["warranty_remaining_days"] <= 30:
            warranty_alerts.append({
                "id": i["id"],
                "name": i["name"],
                "remaining_days": i["warranty_remaining_days"],
            })

    return {
        "total_spent": round(total_spent, 2),
        "active_value": round(active_value, 2),
        "item_count": len(items),
        "active_count": len(active_items),
        "disposed_count": len(disposed),
        "cat_pie": cat_pie,
        "monthly_trend": monthly_trend,
        "yearly_trend": yearly_trend,
        "top_cost_per_day": top_cost_list,
        "warranty_alerts": warranty_alerts,
    }


# ── export ───────────────────────────────────────────────

@app.get("/api/export/json")
def export_json():
    with get_db() as db:
        items = [row_to_dict(r) for r in db.execute("SELECT * FROM items").fetchall()]
    items = [compute_item_stats(i) for i in items]
    path = EXPORTS_DIR / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return FileResponse(path, filename=path.name, media_type="application/json")


@app.get("/api/export/csv")
def export_csv():
    with get_db() as db:
        items = [row_to_dict(r) for r in db.execute("SELECT * FROM items").fetchall()]
    items = [compute_item_stats(i) for i in items]
    path = EXPORTS_DIR / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if items:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=items[0].keys())
            writer.writeheader()
            writer.writerows(items)
    return FileResponse(path, filename=path.name, media_type="text/csv")


# ── backup ───────────────────────────────────────────────

@app.post("/api/backup")
def manual_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUPS_DIR / f"inventory_{ts}.db"
    shutil.copy2(DB_PATH, dest)
    return {"path": str(dest), "time": ts}


def auto_backup():
    """Called once per day via startup check."""
    today = datetime.now().strftime("%Y%m%d")
    existing = list(BACKUPS_DIR.glob(f"inventory_{today}*.db"))
    if not existing:
        shutil.copy2(DB_PATH, BACKUPS_DIR / f"inventory_{today}.db")
        # Keep only last 30 backups
        all_backups = sorted(BACKUPS_DIR.glob("inventory_*.db"))
        for old in all_backups[:-30]:
            old.unlink()


# ── static files ─────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ── run ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  物品仓库启动: http://localhost:8765\n")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
