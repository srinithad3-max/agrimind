"""
Agronomic knowledge base.

Crop stage lengths and crop coefficients (Kc) follow FAO Irrigation & Drainage
Paper 56 (Allen et al., 1998), adjusted to typical Indian seasons.
Yield response factors (Ky) follow FAO Paper 33 (Doorenbos & Kassam).
Base yields are approximate Indian averages for good management (t/ha).
"""
from __future__ import annotations

from datetime import date

GENERIC_STAGE_NAMES = ["Establishment", "Vegetative", "Flowering / Reproductive", "Maturity"]

CROPS: dict[str, dict] = {
    "tomato": dict(
        name="Tomato", family="Solanaceae",
        stages=[("Seedling & establishment", 30), ("Vegetative growth", 40),
                ("Flowering & fruit set", 45), ("Fruit maturity & harvest", 30)],
        kc=(0.60, 1.15, 0.80), ky=1.05, base_yield=25.0,
        t_opt=(20, 27), t_max=35, ph_opt=(6.0, 7.0),
        n_need=300, p_need=25, k_need=250,
        root_depth=1.0, p_depletion=0.40, plantvillage="Tomato",
    ),
    "potato": dict(
        name="Potato", family="Solanaceae",
        stages=[("Sprouting & emergence", 25), ("Vegetative & stolon", 30),
                ("Tuber bulking", 45), ("Maturity", 30)],
        kc=(0.50, 1.15, 0.75), ky=1.10, base_yield=23.0,
        t_opt=(15, 22), t_max=30, ph_opt=(5.2, 6.5),
        n_need=300, p_need=25, k_need=280,
        root_depth=0.5, p_depletion=0.35, plantvillage="Potato",
    ),
    "maize": dict(
        name="Maize", family="Poaceae",
        stages=[("Emergence", 25), ("Vegetative (knee-high)", 40),
                ("Tasseling & silking", 45), ("Grain fill & maturity", 30)],
        kc=(0.30, 1.20, 0.60), ky=1.25, base_yield=3.3,
        t_opt=(21, 30), t_max=36, ph_opt=(5.8, 7.0),
        n_need=320, p_need=22, k_need=200,
        root_depth=1.2, p_depletion=0.55, plantvillage="Corn_(maize)",
    ),
    "rice": dict(
        name="Rice (paddy)", family="Poaceae",
        stages=[("Nursery & transplanting", 30), ("Tillering", 30),
                ("Panicle initiation & flowering", 60), ("Ripening", 30)],
        kc=(1.05, 1.20, 0.90), ky=1.20, base_yield=4.0,
        t_opt=(22, 32), t_max=36, ph_opt=(5.5, 7.0),
        n_need=300, p_need=20, k_need=180,
        root_depth=0.5, p_depletion=0.20, plantvillage=None, paddy=True,
    ),
    "wheat": dict(
        name="Wheat", family="Poaceae",
        stages=[("Crown root initiation", 20), ("Tillering & jointing", 25),
                ("Heading & grain filling", 60), ("Maturity", 30)],
        kc=(0.40, 1.15, 0.25), ky=1.05, base_yield=3.5,
        t_opt=(15, 22), t_max=32, ph_opt=(6.0, 7.5),
        n_need=320, p_need=22, k_need=180,
        root_depth=1.2, p_depletion=0.55, plantvillage=None,
    ),
    "cotton": dict(
        name="Cotton", family="Malvaceae",
        stages=[("Emergence", 30), ("Square formation", 50),
                ("Flowering & boll development", 60), ("Boll opening", 55)],
        kc=(0.35, 1.18, 0.60), ky=0.85, base_yield=1.5,
        t_opt=(21, 32), t_max=38, ph_opt=(6.0, 8.0),
        n_need=280, p_need=20, k_need=200,
        root_depth=1.3, p_depletion=0.65, plantvillage=None,
    ),
    "chilli": dict(
        name="Chilli / Pepper", family="Solanaceae",
        stages=[("Transplant establishment", 30), ("Vegetative", 35),
                ("Flowering & fruiting", 40), ("Harvest", 20)],
        kc=(0.60, 1.05, 0.90), ky=1.10, base_yield=2.5,
        t_opt=(20, 30), t_max=35, ph_opt=(6.0, 7.0),
        n_need=280, p_need=22, k_need=220,
        root_depth=0.7, p_depletion=0.30, plantvillage="Pepper,_bell",
    ),
    "groundnut": dict(
        name="Groundnut", family="Fabaceae",
        stages=[("Emergence", 25), ("Vegetative & pegging", 35),
                ("Pod development", 45), ("Maturity", 25)],
        kc=(0.40, 1.15, 0.60), ky=0.70, base_yield=1.8,
        t_opt=(22, 30), t_max=35, ph_opt=(6.0, 7.0),
        n_need=200, p_need=22, k_need=180,
        root_depth=0.7, p_depletion=0.50, plantvillage=None,
    ),
}

# Available water capacity, mm of water per metre of soil depth
SOILS = {
    "red":    dict(name="Red soil (Alfisol)", awc=120, perc=6),
    "black":  dict(name="Black cotton soil (Vertisol)", awc=200, perc=2),
    "loamy":  dict(name="Loamy / alluvial", awc=150, perc=4),
    "sandy":  dict(name="Sandy", awc=80, perc=10),
    "clay":   dict(name="Clay", awc=190, perc=2),
}

IRRIGATION_EFFICIENCY = {"drip": 0.90, "sprinkler": 0.75, "flood": 0.60}

LEGUMES = {"groundnut", "soybean", "chickpea", "pigeonpea", "greengram", "blackgram", "beans", "pea"}
FAMILY_OF = {k: v["family"] for k, v in CROPS.items()}
FAMILY_OF.update({"soybean": "Fabaceae", "chickpea": "Fabaceae", "pigeonpea": "Fabaceae",
                  "greengram": "Fabaceae", "blackgram": "Fabaceae", "brinjal": "Solanaceae",
                  "onion": "Amaryllidaceae", "fallow": None, "none": None})

STAGE_DISEASE_WEIGHT = [0.6, 0.8, 1.0, 0.5]   # how much a disease hurts yield per stage
STAGE_HEAT_WEIGHT = [0.3, 0.5, 1.0, 0.4]      # flowering is most heat-sensitive
STAGE_WATER_WEIGHT = [0.6, 0.8, 1.0, 0.5]


def crop(key: str) -> dict:
    return CROPS.get(key, CROPS["tomato"])


def growth_stage(crop_key: str, sowing: date, today: date | None = None) -> dict:
    """Derive growth stage, progress and the FAO-56 Kc for today."""
    c = crop(crop_key)
    today = today or date.today()
    das = max(0, (today - sowing).days)          # days after sowing
    lengths = [l for _, l in c["stages"]]
    total = sum(lengths)
    acc, idx = 0, len(lengths) - 1
    for i, l in enumerate(lengths):
        if das < acc + l:
            idx = i
            break
        acc += l
    else:
        acc = total - lengths[-1]
    day_in_stage = das - acc
    return dict(
        das=das, total_days=total, index=idx,
        name=c["stages"][idx][0], generic=GENERIC_STAGE_NAMES[idx],
        day_in_stage=min(day_in_stage, lengths[idx]), stage_length=lengths[idx],
        progress=min(1.0, das / total), days_to_harvest=max(0, total - das),
        kc=kc_for_day(crop_key, das), stages=[dict(name=n, days=l) for n, l in c["stages"]],
        kc_curve=[round(kc_for_day(crop_key, d), 3) for d in range(0, total + 1, 5)],
        past_harvest=das > total,
    )


def kc_for_day(crop_key: str, das: int) -> float:
    """Piece-wise linear FAO-56 crop coefficient curve."""
    c = crop(crop_key)
    kc_ini, kc_mid, kc_end = c["kc"]
    l1, l2, l3, l4 = [l for _, l in c["stages"]]
    if das <= l1:
        return kc_ini
    if das <= l1 + l2:
        return kc_ini + (kc_mid - kc_ini) * (das - l1) / l2
    if das <= l1 + l2 + l3:
        return kc_mid
    if das <= l1 + l2 + l3 + l4:
        return kc_mid + (kc_end - kc_mid) * (das - l1 - l2 - l3) / l4
    return kc_end


def root_depth(crop_key: str, das: int) -> float:
    """Effective root depth grows from 40% to 100% of max by end of development."""
    c = crop(crop_key)
    l1, l2 = c["stages"][0][1], c["stages"][1][1]
    frac = 0.4 + 0.6 * min(1.0, das / (l1 + l2))
    return c["root_depth"] * frac
