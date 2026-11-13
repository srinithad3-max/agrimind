"""
Crop Disease Identification Agent
- CNN (MobileNetV3 trained on PlantVillage) identifies the disease
- Grad-CAM shows which part of the leaf drove the decision
- OpenCV segmentation measures lesion severity (% of leaf area)
- Cross-checks the photo against the farmer's declared crop
- Uses the Weather Agent's humidity outlook to project disease spread
"""
from __future__ import annotations

from app.agents.base import Agent
from app.core import diseases
from app.core.crops import crop
from app.ml.leaf_cv import analyze_leaf, to_bgr
from app.ml.disease_model import get_model, pil_from_bytes


def project_spread(sev0: float, info: dict, days: list[dict], treated: bool) -> list[float]:
    """Logistic disease-progress curve over the forecast week."""
    s, out = max(sev0, 0.0), [round(sev0, 4)]
    for d in days:
        if info["healthy"] or s == 0:
            out.append(round(s, 4))
            continue
        weather_boost = 1.0 if (not info["humid"] or d["fungal"]) else 0.35
        r = (0.04 + 0.22 * info["aggressive"]) * weather_boost
        if treated:
            r *= 0.15 if info["pathogen"] in ("fungal", "oomycete", "bacterial", "pest") else 0.6
        s = min(0.95, s + r * s * (1 - s))
        out.append(round(s, 4))
    return out


class DiseaseAgent(Agent):
    id, name, icon = "disease", "Disease Agent", "🔬"
    reads = ["leaf.image", "weather.forecast", "crop.stage"]
    publishes = ["disease.diagnosis"]

    def run(self) -> dict:
        ctx = self.bb.context
        img_bytes = ctx.get("image")
        wx = self.bb.get("weather.forecast")
        days = wx["daily"] if wx else []
        c = crop(ctx["crop"])

        if not img_bytes:
            self.say("No leaf photo uploaded. Running weather-based disease-risk screening only.")
            fd = wx["summary"]["fungal_days"] if wx else 0
            risk = "high" if fd >= 4 else "medium" if fd >= 2 else "low"
            out = dict(has_image=False, label=None, healthy=True, name="No image", severity=0.0,
                       risk_level=risk, pathogen="none", aggressive=0.0, humid=False,
                       spread_untreated=[0.0] * (len(days) + 1), spread_treated=[0.0] * (len(days) + 1))
            self.bb.publish("disease.diagnosis", out, self.id)
            if risk != "low":
                self.say(f"Weather-only disease risk is {risk.upper()} ({fd} humid days). Recommend field scouting.",
                         to="advisory", level="warn")
            return out

        self.say("Analysing leaf image: segmentation + lesion measurement…")
        cv = analyze_leaf(to_bgr(img_bytes))
        model = get_model()
        method, top, gradcam, conf = "cv", [], None, None

        if model.ready:
            self.say(f"Running CNN classifier ({model.info}) with Grad-CAM…")
            pred = model.predict(pil_from_bytes(img_bytes))
            top, gradcam = pred["top"], pred["gradcam"]
            label, conf = top[0]["label"], top[0]["prob"]
            info = diseases.lookup(label)
            method = "cnn"
        else:
            label = None
            info = dict(diseases.SYMPTOM_FALLBACK[cv["symptom"]])
            info.update(plant=None, healthy=info["pathogen"] == "none")
            conf = None
            self.say("CNN weights not found. Using colour-texture heuristics (train the CNN for exact disease).",
                     level="warn")

        severity = cv["severity"]
        notes = []
        if method == "cnn":
            if info["healthy"] and severity >= 0.15:
                notes.append(f"CNN says healthy but {severity:.0%} of the leaf is discoloured - "
                             "possible nutrient stress or senescence. Take a second photo.")
                severity = severity * 0.5
            elif info["healthy"]:
                severity = 0.0
            elif severity < 0.03:
                severity = 0.05      # CNN sees disease the colour mask missed (early stage)
            if conf is not None and conf < 0.55:
                notes.append(f"Low confidence ({conf:.0%}). Retake photo in daylight, single leaf, plain background.")

        mismatch = None
        expected = c.get("plantvillage")
        if method == "cnn" and info.get("plant") and expected and info["plant"] != expected:
            mismatch = diseases.pretty_plant(info["plant"])
            notes.append(f"Photo looks like a {mismatch} leaf, but the field is registered as {c['name']}.")

        untreated = project_spread(severity, info, days, treated=False)
        treated = project_spread(severity, info, days, treated=True)

        out = dict(
            has_image=True, method=method, label=label, name=info["name"], plant=diseases.pretty_plant(info.get("plant")),
            confidence=conf, top=top, healthy=info["healthy"], pathogen=info["pathogen"],
            aggressive=info["aggressive"], humid=info["humid"],
            chemical=info.get("chemical", ""), organic=info.get("organic", ""), prevention=info.get("prevention", ""),
            severity=round(severity, 4), severity_band=cv["severity_band"], lesion_count=cv["lesion_count"],
            symptom=cv["symptom"], overlay=cv["overlay"], original=cv["original"], gradcam=gradcam,
            spread_untreated=untreated, spread_treated=treated, notes=notes, mismatch=mismatch,
        )
        self.bb.publish("disease.diagnosis", out, self.id)

        if info["healthy"]:
            self.say("Leaf looks healthy. No disease detected.", level="ok")
        else:
            c_txt = f" ({conf:.0%} confidence)" if conf else ""
            self.say(f"Detected {info['name']}{c_txt} · {info['pathogen']} pathogen · "
                     f"{severity:.0%} leaf area affected, {cv['lesion_count']} lesions.", level="alert")
            if untreated[-1] > severity + 0.02:
                self.say(f"If untreated, severity could reach {untreated[-1]:.0%} in 7 days "
                         f"(vs {treated[-1]:.0%} with treatment).", to="yield", level="warn")
            if info["humid"]:
                self.say("Pathogen spreads via leaf wetness: please avoid overhead/flood irrigation "
                         "and schedule early-morning watering.", to="irrigation", level="warn")
        for n in notes:
            self.say(n, level="warn")
        return out
