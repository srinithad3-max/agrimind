"""
Agricultural Advisory Agent (the "head" agent)
Reads everything on the blackboard and turns it into ONE prioritised,
growth-stage-aware action list. Every recommendation carries:
  - priority (1 = act now ... 4 = good practice)
  - the reason ("why"), and which agents contributed
  - a headline in English / Hindi / Telugu
Optionally an LLM writes a friendly summary in the farmer's language.
"""
from __future__ import annotations

import json

from app.agents.base import Agent
from app.core import i18n, llm
from app.core.crops import crop, FAMILY_OF

PRIORITY_LABEL = {1: "Act now", 2: "This week", 3: "Plan ahead", 4: "Good practice"}


class AdvisoryAgent(Agent):
    id, name, icon = "advisory", "Advisory Agent", "🧑‍🌾"
    reads = ["*"]
    publishes = ["advisory.plan"]

    def rec(self, key, priority, category, detail, why, sources, **params):
        self.recs.append(dict(key=key, priority=priority, priority_label=PRIORITY_LABEL[priority],
                              category=category, params=params, detail=detail, why=why, sources=sources,
                              title={lg: i18n.render(key, params, lg) for lg in ("en", "hi", "te")}))

    def run(self) -> dict:
        self.recs = []
        ctx = self.bb.context
        c = crop(ctx["crop"])
        st = self.bb.get("crop.stage")
        wx = self.bb.get("weather.forecast")
        days, ws = wx["daily"], wx["summary"]
        dis = self.bb.get("disease.diagnosis")
        irr = self.bb.get("irrigation.plan")
        yl = self.bb.get("yield.forecast")
        stage_i = st["index"]
        self.say(f"Combining 4 agent reports for {c['name']} at '{st['name']}' stage (day {st['das']}).")

        # ---------------- disease ----------------
        rain_soon = [i for i in (0, 1) if i < len(days) and days[i]["rain"] >= 5 and days[i]["rain_prob"] >= 50]
        if dis.get("mismatch"):
            self.rec("mismatch", 1, "disease", "The diagnosis may not apply to your crop. Upload a clear photo "
                     "of a single affected leaf from this field.", "Disease Agent's plant check disagrees with "
                     "the registered crop.", ["disease"], img_crop=dis["mismatch"])
        if dis.get("has_image") and not dis["healthy"]:
            product = dis["chemical"].split(":")[-1].split(" or ")[0].split(";")[0].split("(")[0].strip() or "a protectant fungicide"
            sev, sev7 = dis["severity"], dis["spread_untreated"][-1]
            late = stage_i == 3 and sev < 0.1
            why = (f"{dis['name']} covers {sev:.0%} of leaf area; untreated it may reach {sev7:.0%} in 7 days "
                   f"(vs {dis['spread_treated'][-1]:.0%} if treated).")
            if dis["pathogen"] == "viral":
                self.rec("virus_remove", 1, "disease", f"{dis['chemical']}. {dis['organic']}.", why,
                         ["disease"])
            elif 0 in rain_soon:
                dw = ws["dry_window"]
                day = days[dw]["day"] if dw is not None else "the next dry day"
                self.rec("spray_after_rain", 1 if not late else 3, "disease",
                         f"Use {dis['chemical']}. Spraying in rain washes the product off. "
                         f"Organic option: {dis['organic']}.",
                         why + f" Rain today ({days[0]['rain']:.0f} mm).", ["disease", "weather"], day=day)
            elif 1 in rain_soon:
                self.rec("spray_now", 1 if not late else 3, "disease",
                         f"Use {dis['chemical']}; add a sticker/spreader so it stays rainfast. Needs ~6 dry hours. "
                         f"Organic option: {dis['organic']}.",
                         why + f" Rain of {days[1]['rain']:.0f} mm arrives {days[1]['day']}, and wet weather "
                         "will accelerate spread.", ["disease", "weather"], product=product)
            else:
                self.rec("spray_soon", 1 if (sev >= 0.1 and not late) else 2, "disease",
                         f"Use {dis['chemical']}. Organic option: {dis['organic']}. Spray in the evening, "
                         "not in strong wind.", why, ["disease", "weather"], product=product)
            if dis.get("prevention"):
                fam = c["family"]
                self.rec("rotation", 4, "disease", dis["prevention"] + ".",
                         "Pathogens survive in crop residue and soil and re-infect related crops.",
                         ["disease"], family=fam)
        elif ws["fungal_days"] >= 4 and stage_i < 3:
            self.rec("preventive_spray", 2, "disease",
                     "Spray a protectant (Mancozeb 2.5 g/L) on a dry morning and scout lower leaves daily.",
                     f"{ws['fungal_days']} of the next 7 days are humid/wet: classic conditions for blight and "
                     "leaf-spot outbreaks.", ["weather", "disease"])
        elif dis.get("has_image"):
            self.rec("healthy", 4, "disease", "Re-check with a photo every 5-7 days, especially after rain.",
                     "Disease Agent found no disease symptoms.", ["disease"])
        elif ws["fungal_days"] >= 2:
            self.rec("scout", 2, "disease", "Walk the field and photograph any spotted or yellowing leaves "
                     "for the Disease Agent.", f"{ws['fungal_days']} humid days ahead.", ["weather"])

        # ---------------- irrigation ----------------
        irrigate = [r for r in irr["schedule"] if r["status"] == "irrigate"]
        if irr["method_recommended"] != irr["method"] and not irr.get("paddy"):
            self.rec("switch_drip", 2, "irrigation",
                     f"If drip is not available, use furrow irrigation at soil level, at {irr['best_time']}.",
                     "Wet leaves spread the detected disease.", ["irrigation", "disease"], method=irr["method"])
        if irrigate:
            mm = round(sum(r["gross_mm"] for r in irrigate) / len(irrigate))
            d_txt = ", ".join(r["day"] for r in irrigate)
            litres = sum(r["litres"] for r in irrigate)
            hrs = sum(r["pump_hours"] for r in irrigate)
            self.rec("irrigate", 1 if irrigate[0] is irr["schedule"][0] else 2, "irrigation",
                     f"≈{litres/1000:,.0f} kL in total (~{hrs:.1f} h of a 5 HP pump) at {irr['best_time']}. "
                     f"{irr['notes'][-1] if irr['notes'] else ''}",
                     f"Root-zone water will fall below the safe level for the '{st['name']}' stage. "
                     f"Plan uses {irr['water_saved_pct']:.0%} less water than calendar flood irrigation.",
                     ["irrigation", "weather"], mm=mm, days=d_txt)
        elif ws["total_rain"] >= 10:
            self.rec("skip_irrigation", 2, "irrigation",
                     "Rainfall will refill the root zone. Saves water and pumping cost.",
                     f"Forecast {ws['total_rain']} mm rain covers crop demand of {irr['total_etc']:.0f} mm.",
                     ["irrigation", "weather"], rain=round(ws["total_rain"]))
        else:
            self.rec("no_irrigation", 3, "irrigation", "Current soil moisture is enough for this week.",
                     f"Soil water stays above the stress threshold for all 7 days.", ["irrigation"])
        if irr.get("paddy"):
            self.rec("awd", 3, "irrigation", irr["notes"][-1], "AWD is recommended by IRRI/ICAR and cuts methane "
                     "emissions too.", ["irrigation"])

        # ---------------- weather & stage ----------------
        for r in wx["risks"]:
            if r["type"] == "heat":
                d = days[r["day"]]
                self.rec("heat", 1 if stage_i == 2 else 2, "weather",
                         "Give light irrigation in the evening, mulch the soil, and avoid spraying in midday heat."
                         + (" Heat at flowering causes flower drop and poor fruit/grain set." if stage_i == 2 else ""),
                         r["text"], ["weather", "yield"], temp=round(d["tmax"]), day=d["day"])
            elif r["type"] == "heavy_rain":
                d = days[r["day"]]
                self.rec("heavy_rain", 2, "weather",
                         "Open field drains to avoid waterlogging. Don't apply urea/fertiliser just before heavy "
                         "rain: it leaches away.", r["text"], ["weather"], day=d["day"])
                break
        if stage_i == 3 and not st["past_harvest"]:
            self.rec("harvest", 2, "stage", f"About {st['days_to_harvest']} days to harvest. Stop irrigation 7-10 "
                     "days before harvest.", "Crop is in the final growth stage.", ["irrigation", "weather"])

        # ---------------- nutrition (stage-aware) ----------------
        lim = dict(yl["limiting"])
        if lim.get("nitrogen", 1) < 0.9 and stage_i <= 1:
            self.rec("nitrogen", 2, "nutrition",
                     "Apply urea in 2 splits as per your Soil Health Card. Avoid applying before heavy rain.",
                     f"Nitrogen factor {lim['nitrogen']:.2f}: vegetative stage is when N is used most.",
                     ["yield"])
        if lim.get("potassium", 1) < 0.92 and stage_i in (1, 2):
            self.rec("potassium", 3, "nutrition", "Apply muriate of potash (MOP) or a foliar 13-0-45 spray (5 g/L).",
                     f"Potassium factor {lim['potassium']:.2f}: K drives fruit/grain filling.", ["yield"])
        if lim.get("phosphorus", 1) < 0.9 and stage_i <= 1:
            self.rec("phosphorus", 3, "nutrition", "Band-place DAP/SSP near the root zone.",
                     f"Phosphorus factor {lim['phosphorus']:.2f}.", ["yield"])
        lo, hi = c["ph_opt"]
        if ctx["ph"] < lo - 0.3:
            self.rec("ph_acid", 4, "nutrition", "Apply lime before the next season based on a soil test.",
                     f"Optimal pH for {c['name']} is {lo}-{hi}.", ["yield"], ph=ctx["ph"])
        elif ctx["ph"] > hi + 0.3:
            self.rec("ph_alk", 4, "nutrition", "Apply gypsum and well-rotted FYM; use acid-forming fertilisers.",
                     f"Optimal pH for {c['name']} is {lo}-{hi}.", ["yield"], ph=ctx["ph"])

        # ---------------- history / rotation ----------------
        prev = ctx.get("prev_crop") or "none"
        if FAMILY_OF.get(prev) and FAMILY_OF.get(prev) == c["family"] and not any(r["key"] == "rotation" for r in self.recs):
            self.rec("rotation", 3, "history",
                     f"Previous crop ({prev}) is from the same family, so soil-borne disease carry-over risk "
                     "is higher. Next season, follow with a legume or cereal.",
                     "Continuous cropping of one family builds up pathogens.", ["disease", "yield"],
                     family=c["family"])

        # ---------------- yield value ----------------
        if yl["saved_quintals"] > 0.01 * yl["potential"]["total_q"]:
            self.rec("yield_protect", 2, "yield",
                     f"No action: {yl['no_action']['q_acre']} q/acre → with plan: {yl['with_plan']['q_acre']} q/acre "
                     f"(at ~₹{yl['price_per_q']:,}/q).",
                     f"Losses attributed to disease {yl['attribution']['disease']:.0%}, water stress "
                     f"{yl['attribution']['water']:.0%}.", ["yield"],
                     q=yl["saved_quintals"], rs=f"{yl['revenue_protected']:,}")

        self.recs.sort(key=lambda r: r["priority"])
        summary = {lg: " • ".join(r["title"][lg] for r in self.recs[:3]) for lg in ("en", "hi", "te")}
        lang = ctx.get("lang", "en")
        ai = None
        if llm.enabled():
            self.say("Asking the language model for a farmer-friendly summary…")
            ai = llm.chat([
                dict(role="system", content="You are an Indian agricultural extension officer. Write a short, warm, "
                     "practical voice message (max 90 words) for a small farmer. No markdown. Use the requested "
                     "language and simple words. Only use facts given."),
                dict(role="user", content=f"Language: {dict(en='English', hi='Hindi', te='Telugu')[lang]}\n"
                     f"Crop: {c['name']}, stage: {st['name']}\nActions:\n" +
                     json.dumps([dict(action=r["title"]["en"], detail=r["detail"]) for r in self.recs[:5]],
                                ensure_ascii=False)),
            ])

        out = dict(recommendations=self.recs, summary=summary, ai_summary=ai, ai_lang=lang if ai else None,
                   counts={p: sum(r["priority"] == p for r in self.recs) for p in (1, 2, 3, 4)})
        self.bb.publish("advisory.plan", out, self.id)
        n1 = out["counts"][1]
        self.say(f"Final plan ready: {len(self.recs)} actions, {n1} urgent. Top: {self.recs[0]['title']['en'] if self.recs else '-'}",
                 level="ok")
        return out
