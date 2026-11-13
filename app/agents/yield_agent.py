"""
Yield Prediction Agent
- Gradient-boosted model predicts yield from soil, weather, water stress,
  disease severity and growth stage
- Runs three scenarios: potential (no stress), no action, and following the
  AgriMind plan, so the farmer sees exactly what the advice is worth
- Attributes the predicted loss to its causes (disease / water / heat / soil)
"""
from __future__ import annotations

import pandas as pd

from app.agents.base import Agent
from app.core.crops import crop, LEGUMES
from app.ml import yield_model

Q_PER_ACRE = 10 / 2.4711          # 1 t/ha = 4.047 quintal/acre
PRICE_PER_Q = dict(tomato=1200, potato=1200, maize=2225, rice=2300, wheat=2425,
                   cotton=7121, chilli=12000, groundnut=6783)   # approx. MSP / mandi, Rs per quintal


class YieldAgent(Agent):
    id, name, icon = "yield", "Yield Agent", "📈"
    reads = ["farm.soil", "weather.forecast", "irrigation.plan", "disease.diagnosis", "crop.stage"]
    publishes = ["yield.forecast"]

    def run(self) -> dict:
        ctx = self.bb.context
        c = crop(ctx["crop"])
        stage = self.bb.get("crop.stage")
        wx = self.bb.get("weather.forecast")["summary"]
        irr = self.bb.get("irrigation.plan")
        dis = self.bb.get("disease.diagnosis")

        base = dict(crop=ctx["crop"], stage=stage["index"], n=ctx["n"], p=ctx["p"], k=ctx["k"], ph=ctx["ph"],
                    temp_mean=wx["mean_temp"], heat_days=wx["heat_days"],
                    disease_aggr=dis.get("aggressive", 0.0),
                    prev_legume=int(ctx.get("prev_crop") in LEGUMES))
        scenarios = {
            "potential": dict(base, water_ratio=1.0, disease_severity=0.0, heat_days=round(wx["heat_days"] * 0.6)),
            "no_action": dict(base, water_ratio=irr["water_ratio_none"],  # noqa
                              disease_severity=dis["spread_untreated"][-1]),
            # well-timed irrigation also cools the canopy, softening heat stress
            "with_plan": dict(base, water_ratio=max(irr["water_ratio_plan"], 0.97),
                              disease_severity=dis["spread_treated"][-1],
                              heat_days=round(wx["heat_days"] * 0.6)),
            # counterfactuals for attribution
            "fix_disease": dict(base, water_ratio=irr["water_ratio_none"], disease_severity=0.0),
            "fix_water": dict(base, water_ratio=1.0, disease_severity=dis["spread_untreated"][-1]),
        }
        preds = dict(zip(scenarios, yield_model.predict(list(scenarios.values()))))
        pot = preds["potential"]
        # monotonic guard (tree models can wobble slightly)
        preds["no_action"] = min(preds["no_action"], pot)
        preds["with_plan"] = min(max(preds["with_plan"], preds["no_action"]), pot)

        loss_disease = max(0.0, preds["fix_disease"] - preds["no_action"])
        loss_water = max(0.0, preds["fix_water"] - preds["no_action"])
        f = yield_model.factors(pd.DataFrame([scenarios["potential"]])).iloc[0]
        limiting = sorted(((k, round(float(v), 3)) for k, v in f.items() if k not in ("water", "disease")),
                          key=lambda t: t[1])

        def pack(t_ha):
            q_acre = t_ha * Q_PER_ACRE
            return dict(t_ha=round(float(t_ha), 2), q_acre=round(float(q_acre), 1),
                        total_q=round(float(q_acre * ctx["area"]), 1),
                        change_pct=round(float((t_ha - pot) / pot), 4) if pot else 0.0)

        price = PRICE_PER_Q.get(ctx["crop"], 2000)
        saved_q = (preds["with_plan"] - preds["no_action"]) * Q_PER_ACRE * ctx["area"]
        out = dict(
            potential=pack(pot), no_action=pack(preds["no_action"]), with_plan=pack(preds["with_plan"]),
            benchmark_t_ha=c["base_yield"],
            attribution=dict(disease=round(float(loss_disease / pot), 4) if pot else 0,
                             water=round(float(loss_water / pot), 4) if pot else 0,
                             heat_soil=round(float(1 - pot / c["base_yield"]), 4)),
            limiting=limiting, price_per_q=price,
            revenue_protected=round(float(saved_q * price)), saved_quintals=round(float(saved_q), 1),
            model=yield_model.load()["metrics"],
        )
        if ctx.get("last_yield"):
            last = ctx["last_yield"]                      # quintal / acre
            out["vs_last_season_pct"] = round(float((out["with_plan"]["q_acre"] - last) / last), 4)
            out["last_yield_q_acre"] = last

        self.bb.publish("yield.forecast", out, self.id)
        self.say(f"Potential {out['potential']['q_acre']} q/acre. No action: {out['no_action']['q_acre']} q/acre "
                 f"({out['no_action']['change_pct']:+.0%}). With plan: {out['with_plan']['q_acre']} q/acre "
                 f"({out['with_plan']['change_pct']:+.0%}).")
        if saved_q > 0.01 * pot * Q_PER_ACRE * ctx["area"]:
            self.say(f"Following the plan protects ≈{saved_q:.1f} quintals ≈ ₹{out['revenue_protected']:,} "
                     f"on {ctx['area']:g} acre(s).", to="advisory", level="ok")
        soil_lim = [t for t in limiting if t[0] in ("nitrogen", "phosphorus", "potassium", "soil_ph")]
        if soil_lim and soil_lim[0][1] < 0.92:
            self.say(f"Biggest soil constraint: {soil_lim[0][0].replace('_', ' ')} "
                     f"(factor {soil_lim[0][1]:.2f}). Flagging for nutrient advice.", to="advisory")
        return out
