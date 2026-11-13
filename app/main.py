"""
AgriMind API + dashboard server.
Run:  python run.py     then open http://localhost:8000
API docs (Swagger): http://localhost:8000/docs
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]


def _load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_env()

from app.core import llm  # noqa: E402
from app.core.crops import CROPS, SOILS, growth_stage  # noqa: E402
from app.core.orchestrator import agent_roster, run_pipeline  # noqa: E402
from app.ml import yield_model  # noqa: E402
from app.ml.disease_model import get_model  # noqa: E402

app = FastAPI(title="AgriMind: multi-agent crop intelligence", version="1.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
(ROOT / "samples").mkdir(exist_ok=True)
app.mount("/samples", StaticFiles(directory=ROOT / "samples"), name="samples")

PLACES = {
    "Hyderabad": (17.385, 78.4867), "Warangal": (17.9689, 79.5941), "Karimnagar": (18.4386, 79.1288),
    "Nizamabad": (18.6725, 78.0941), "Khammam": (17.2473, 80.1514), "Nalgonda": (17.0575, 79.2671),
    "Mahabubnagar": (16.7488, 78.0035), "Adilabad": (19.6641, 78.532), "Siddipet": (18.1018, 78.852),
    "Guntur": (16.3067, 80.4365), "Vijayawada": (16.5062, 80.648), "Kurnool": (15.8281, 78.0373),
    "Anantapur": (14.6819, 77.6006), "Nashik": (19.9975, 73.7898), "Pune": (18.5204, 73.8567),
    "Bengaluru": (12.9716, 77.5946), "Ludhiana": (30.901, 75.8573), "Kolar": (13.1367, 78.1292),
}


@app.get("/")
async def index(request: Request):
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
async def health(request: Request):
    dm = get_model()
    ym = yield_model.load()["metrics"]
    return JSONResponse(dict(status="ok", disease_model=dict(ready=dm.ready, info=dm.info),
                             yield_model=dict(r2=ym["r2"], mae_rel=ym["mae_rel"], algorithm=ym["algorithm"],
                                              importance=ym["importance"][:8]),
                             llm=llm.enabled(), agents=agent_roster()))


@app.get("/api/meta")
async def meta(request: Request):
    samples = sorted(p.name for p in (ROOT / "samples").iterdir()
                     if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    return JSONResponse(dict(
        crops={k: dict(name=v["name"], stages=v["stages"], family=v["family"]) for k, v in CROPS.items()},
        soils={k: v["name"] for k, v in SOILS.items()}, places=PLACES, samples=samples))


@app.get("/api/geocode")
async def geocode(request: Request):
    q = request.query_params.get("q", "").strip()
    if q.title() in PLACES:
        lat, lon = PLACES[q.title()]
        return JSONResponse(dict(name=q.title(), lat=lat, lon=lon))
    try:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params=dict(name=q, count=1, country="IN"), timeout=6)
        res = r.json().get("results") or []
        if res:
            g = res[0]
            return JSONResponse(dict(name=f"{g['name']}, {g.get('admin1', '')}".strip(", "),
                                     lat=g["latitude"], lon=g["longitude"]))
    except Exception:
        pass
    return JSONResponse(dict(error=f"Place '{q}' not found"), status_code=404)


@app.get("/api/stage")
async def stage(request: Request):
    qp = request.query_params
    s = growth_stage(qp.get("crop", "tomato"), date.fromisoformat(qp.get("sowing_date")))
    return JSONResponse(s)


def _f(form, key, default, cast=float):
    v = form.get(key)
    try:
        return cast(v) if v not in (None, "") else default
    except ValueError:
        return default


@app.post("/api/analyze")
async def analyze(request: Request):
    """Streams newline-delimited JSON events while the agents work."""
    form = await request.form()
    image = form.get("image")
    img_bytes = None
    if image is not None and hasattr(image, "read"):
        img_bytes = await image.read() or None
    elif form.get("sample"):
        p = ROOT / "samples" / Path(form.get("sample")).name
        img_bytes = p.read_bytes() if p.exists() else None

    place = form.get("place") or "Hyderabad"
    lat, lon = PLACES.get(place, (None, None))
    ctx = dict(
        crop=form.get("crop") or "tomato",
        sowing_date=date.fromisoformat(form.get("sowing_date") or date.today().isoformat()),
        place=place, lat=_f(form, "lat", lat or 17.385), lon=_f(form, "lon", lon or 78.4867),
        soil=form.get("soil") or "red", n=_f(form, "n", 280), p=_f(form, "p", 18), k=_f(form, "k", 220),
        ph=_f(form, "ph", 6.8), moisture=_f(form, "moisture", 60), method=form.get("method") or "flood",
        area=_f(form, "area", 1.0), prev_crop=(form.get("prev_crop") or "none").lower(),
        last_yield=_f(form, "last_yield", None), lang=form.get("lang") or "en",
        scenario=form.get("scenario") or "live", image=img_bytes,
    )
    pace = _f(form, "pace", 0.35)

    def stream():
        for evt in run_pipeline(ctx, pace=pace):
            yield json.dumps(evt, default=str, ensure_ascii=False) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/api/ask")
async def ask(request: Request):
    """Farmer Q&A grounded on the latest agent results."""
    body = await request.json()
    q, ctx, lang = body.get("question", ""), body.get("context", {}), body.get("lang", "en")
    answer = llm.chat([
        dict(role="system", content="You are AgriMind, an agricultural advisor for Indian farmers. Answer in "
             f"{dict(en='English', hi='Hindi', te='Telugu').get(lang, 'English')} in under 80 words, using only "
             "the farm data provided. If unsure, advise contacting the local KVK."),
        dict(role="user", content=f"Farm data: {json.dumps(ctx, ensure_ascii=False)[:6000]}\n\nQuestion: {q}"),
    ])
    if answer:
        return JSONResponse(dict(answer=answer, source="llm"))
    # offline fallback: keyword match against the advisory plan
    recs = ctx.get("recommendations", [])
    ql = q.lower()
    topics = {"irrigation": ["water", "irrigat", "pani", "neeru", "sinchai", "నీరు", "पानी", "सिंचाई"],
              "disease": ["disease", "spray", "spot", "blight", "leaf", "rog", "pest", "తెగులు", "रोग"],
              "weather": ["rain", "weather", "heat", "barish", "varsham", "వర్షం", "बारिश"],
              "yield": ["yield", "harvest", "production", "upaj", "money", "profit", "దిగుబడి", "उपज"],
              "nutrition": ["fertil", "urea", "nitrogen", "potash", "soil", "khad", "ఎరువు", "खाद"]}
    hit = [t for t, kws in topics.items() if any(k in ql for k in kws)]
    picked = [r for r in recs if r.get("category") in hit] or recs[:2]
    if not picked:
        return JSONResponse(dict(answer="Run the agents first, then ask me about your field.", source="rules"))
    text = " ".join(f"{r['title'].get(lang, r['title']['en'])}. {r['detail']}" for r in picked[:2])
    return JSONResponse(dict(answer=text, source="rules"))
