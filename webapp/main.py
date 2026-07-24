from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from dress_agent.config import load_config
from dress_agent.classification import SCENE_CATEGORIES
from dress_agent.storage import ProductRepository
from webapp.runner import AgentRunner


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
STATIC_DIRECTORY = ROOT / "webapp" / "static"
TEMPLATE_DIRECTORY = ROOT / "webapp" / "templates"

app = FastAPI(title="礼服选品 Agent", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIRECTORY)
runner = AgentRunner(CONFIG_PATH)


class RunRequest(BaseModel):
    sites: list[str]


@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run(request: RunRequest) -> dict:
    config = load_config(CONFIG_PATH)
    enabled_sites = {
        name for name, item in config["sites"].items() if item.get("enabled", False)
    }
    selected_sites = list(dict.fromkeys(request.sites))
    invalid_sites = set(selected_sites) - enabled_sites
    if invalid_sites:
        raise HTTPException(status_code=400, detail="Invalid site selection")
    if not selected_sites:
        raise HTTPException(status_code=400, detail="Select at least one site")
    return runner.start(selected_sites)


@app.get("/api/sites")
def sites() -> dict:
    config = load_config(CONFIG_PATH)
    return {
        "items": [
            {"name": name, "base_url": item["base_url"]}
            for name, item in config["sites"].items()
            if item.get("enabled", False)
        ]
    }


@app.get("/api/runs/current")
def current_run() -> dict:
    return runner.state()


@app.get("/api/products")
def products(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
) -> dict:
    if category is not None and category not in SCENE_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid product category")
    config = load_config(CONFIG_PATH)
    database_path = _resolve_path(config["database"]["path"])
    with ProductRepository(database_path) as repository:
        return {
            "items": repository.list_products(
                limit=limit, offset=offset, category=category
            ),
            "total": repository.count_products(category=category),
            "limit": limit,
            "offset": offset,
            "category": category,
        }


@app.get("/api/reports")
def reports() -> dict:
    report_directory = _report_directory()
    items = []
    if report_directory.exists():
        for path in sorted(report_directory.glob("*.md"), reverse=True):
            items.append({"date": path.stem, "name": path.name})
    return {"items": items}


@app.get("/api/reports/{report_date}")
def report(report_date: str) -> FileResponse:
    try:
        date.fromisoformat(report_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report date")
    path = _report_directory() / f"{report_date}.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="text/markdown; charset=utf-8")


def _report_directory() -> Path:
    config = load_config(CONFIG_PATH)
    return _resolve_path(config["reports"]["directory"])


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate
