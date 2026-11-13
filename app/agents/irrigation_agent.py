"""
Irrigation Planning Agent  (FAO-56 soil-water-balance)

  ETc  = Kc(stage) x ET0                      crop water use per day
  TAW  = AWC(soil) x root depth               total available water
  RAW  = p x TAW                              readily available water
  Dr   = Dr(prev) + ETc - effective rain - irrigation   root-zone depletion
  Irrigate when Dr > RAW (stricter at the water-critical flowering stage),
  but postpone if the Weather Agent forecasts enough rain tomorrow.

Paddy uses Alternate Wetting & Drying (AWD), an IRRI/ICAR water-saving method.
"""
from __future__ import annotations

from app.agents.base import Agent
from app.core.crops import crop, kc_for_day, root_depth, SOILS, IRRIGATION_EFFICIENCY

L_PER_MM_ACRE = 4046.86
PUMP_LPS = 10.0  # ~5 HP agricultural pump, litres/second


def eff_rain(mm: float) -> float:
    return 0.0 if mm < 2 else 0.8 * mm


class IrrigationAgent(Agent):
    id, name, icon = "irrigation", "Irrigation Agent", "💧"
    reads = ["weather.forecast", "crop.stage", "disease.diagnosis", "farm.soil"]
    publishes = ["irrigation.plan"]

    def run(self) -> dict:
        ctx = self.bb.context
        c = crop(ctx["crop"])
        stage = self.bb.get("crop.stage")
        wx = self.bb.get("weather.forecast")
        dis = self.bb.get("disease.diagnosis") or {}
        soil = SOILS.get(ctx["soil"], SOILS["loamy"])
        days = wx["daily"]
        das0 = stage["das"]
        area = ctx["area"]
        method = ctx["method"]
        notes = []

        # Disease-aware method choice (cooperation with Disease Agent)
        if dis.get("humid") and not dis.get("healthy", True) and method in ("sprinkler", "flood"):
            notes.append(f"Disease Agent reports a leaf-wetness pathogen; switching {method} to drip / "
                         "furrow at soil level is advised.")
            self.say(f"Received disease alert. Advising against {method}: wet foliage spreads "
                     f"{dis.get('name', 'the disease')}. Recommending drip at soil level.", to="disease")
            method_rec = "drip"
        else:
            method_rec = method
        eff = IRRIGATION_EFFICIENCY[method_rec]
        if c.get("paddy"):
            method_rec, eff = "flood", 0.75   # field-channel delivery to a bunded paddy

        if c.get("paddy"):
            plan = self._paddy(days, das0, ctx, soil, c)
        else:
            plan = self._upland(days, das0, ctx, soil, c, stage)

        for row in plan["schedule"]:
            row["gross_mm"] = round(row["net_mm"] / eff, 1) if row["net_mm"] else 0.0
            row["litres"] = round(row["gross_mm"] * L_PER_MM_ACRE * area)
            row["pump_hours"] = round(row["litres"] / PUMP_LPS / 3600, 1)

        total_gross = sum(r["gross_mm"] for r in plan["schedule"])
        total_etc = sum(r["etc"] for r in plan["schedule"])
        # conventional practice: flood irrigation that refills the deficit and ignores the rain forecast
        conventional = (plan.get("initial_deficit", 50.0) + total_etc + (7 * soil["perc"] if c.get("paddy") else 0)) \
            / IRRIGATION_EFFICIENCY["flood"]
        saved_pct = max(0.0, 1 - total_gross / conventional) if conventional > 0 else 0.0

        irrigate_days = [r for r in plan["schedule"] if r["status"] == "irrigate"]
        out = dict(
            method=method, method_recommended=method_rec, efficiency=eff, soil=soil["name"],
            schedule=plan["schedule"], taw=plan.get("taw"), raw=plan.get("raw"),
            total_net_mm=round(sum(r["net_mm"] for r in plan["schedule"]), 1),
            total_gross_mm=round(total_gross, 1), total_etc=round(total_etc, 1),
            total_litres=round(total_gross * L_PER_MM_ACRE * area),
            conventional_litres=round(conventional * L_PER_MM_ACRE * area),
            water_saved_pct=round(saved_pct, 3),
            water_ratio_plan=plan["ratio_plan"], water_ratio_none=plan["ratio_none"],
            best_time="5:30-8:00 AM" if dis.get("humid") else "early morning or evening",
            paddy=bool(c.get("paddy")), notes=notes + plan.get("notes", []),
        )
        self.bb.publish("irrigation.plan", out, self.id)

        if irrigate_days:
            d_txt = ", ".join(f"{r['day']} ({r['gross_mm']:.0f} mm)" for r in irrigate_days)
            self.say(f"Plan: irrigate on {d_txt} via {method_rec}. Total {out['total_litres']/1000:,.0f} kL "
                     f"for {area:g} acre(s), {saved_pct:.0%} less than calendar flood irrigation.")
        else:
            self.say("No irrigation needed this week: soil moisture + forecast rain cover crop demand.", level="ok")
        for r in plan["schedule"]:
            if r["status"] == "postponed":
                self.say(f"Postponed {r['day']} irrigation: Weather Agent forecasts rain next day.", to="weather")
        self.say(f"Without irrigation, water-stress factor would be {plan['ratio_none']:.2f} "
                 f"(1.0 = no stress); with plan {plan['ratio_plan']:.2f}.", to="yield")
        return out

    # ------------------------------------------------------------------ upland
    def _upland(self, days, das0, ctx, soil, c, stage):
        zr = root_depth(ctx["crop"], das0)
        taw = soil["awc"] * zr
        p = c["p_depletion"]
        raw = p * taw
        critical = stage["index"] == 2      # flowering: irrigate earlier
        trigger = raw * (0.8 if critical else 1.0)
        dr = taw * (1 - ctx["moisture"] / 100)
        dr_none = dr
        sched, ks_plan, ks_none = [], [], []
        for i, d in enumerate(days):
            kc = kc_for_day(ctx["crop"], das0 + i)
            etc = kc * d["et0"]
            pe = eff_rain(d["rain"])
            dr = max(0.0, dr + etc - pe)
            dr_none = min(taw, max(0.0, dr_none + etc - pe))
            status, net = "ok", 0.0
            if pe >= 5:
                status = "rain"
            if dr > trigger:
                nxt = days[i + 1] if i + 1 < len(days) else None
                if nxt and nxt["rain_prob"] >= 60 and eff_rain(nxt["rain"]) >= 0.6 * dr and dr < 0.9 * taw:
                    status = "postponed"
                else:
                    # rain-aware deficit irrigation: leave room for rain expected in the next 2 days
                    coming = sum(eff_rain(x["rain"]) for x in days[i + 1:i + 3] if x["rain_prob"] >= 50)
                    net = max(dr - coming, dr - raw * 0.5, 0.25 * dr)
                    status = "irrigate"
                    dr -= net
            ks = 1.0 if dr <= raw else max(0.0, (taw - dr) / ((1 - p) * taw))
            ks_n = 1.0 if dr_none <= raw else max(0.0, (taw - dr_none) / ((1 - p) * taw))
            ks_plan.append(ks)
            ks_none.append(ks_n)
            sched.append(dict(day=d["day"], date=d["date"], kc=round(kc, 2), et0=d["et0"], etc=round(etc, 2),
                              rain=d["rain"], eff_rain=round(pe, 1), net_mm=round(net, 1), status=status,
                              depletion_pct=round(min(1.0, dr / taw), 3),
                              depletion_none_pct=round(dr_none / taw, 3)))
        notes = [f"Root zone {zr:.2f} m, TAW {taw:.0f} mm, irrigation trigger at {trigger:.0f} mm depletion"
                 + (" (tightened for flowering stage)." if critical else ".")]
        return dict(schedule=sched, taw=round(taw, 1), raw=round(raw, 1), notes=notes, initial_deficit=taw * (1 - ctx["moisture"] / 100),
                    ratio_plan=round(sum(ks_plan) / len(ks_plan), 3),
                    ratio_none=round(sum(ks_none) / len(ks_none), 3))

    # ------------------------------------------------------------------ paddy
    def _paddy(self, days, das0, ctx, soil, c):
        m = ctx["moisture"]
        w = 50.0 if m >= 85 else 0.0 if m >= 60 else -100.0   # water level, mm (+ponded / -below surface)
        w_none = w
        sched, ks_plan, ks_none = [], [], []
        for i, d in enumerate(days):
            das = das0 + i
            kc = kc_for_day(ctx["crop"], das)
            etc = kc * d["et0"]
            loss = etc + soil["perc"]
            w = w - loss + d["rain"]
            w_none = max(-300.0, w_none - loss + d["rain"])
            w = min(w, 100.0)
            w_none = min(w_none, 100.0)
            flowering = c["stages"][0][1] + c["stages"][1][1] <= das < sum(l for _, l in c["stages"][:3])
            threshold = 0.0 if flowering else -150.0           # AWD: let water drop 15 cm below surface
            status, net = ("rain" if d["rain"] >= 5 else "ok"), 0.0
            if w < threshold:
                nxt = days[i + 1] if i + 1 < len(days) else None
                if nxt and nxt["rain_prob"] >= 60 and nxt["rain"] >= 20 and w > -150:
                    status = "postponed"
                else:
                    status, net = "irrigate", 50.0 - w
                    w = 50.0
            ks_plan.append(1.0 if w > -150 else 0.85)
            thr_none = 0.0 if flowering else -150.0     # drying out at flowering is what hurts paddy most
            ks_none.append(1.0 if w_none > thr_none else max(0.3, 1 + (w_none - thr_none) / 250))
            sched.append(dict(day=d["day"], date=d["date"], kc=round(kc, 2), et0=d["et0"], etc=round(etc, 2),
                              rain=d["rain"], eff_rain=d["rain"], net_mm=round(net, 1), status=status,
                              water_level_mm=round(w), depletion_pct=round(max(0.0, -w) / 300, 3),
                              depletion_none_pct=round(max(0.0, -w_none) / 300, 3)))
        initial = 100.0 - (50.0 if m >= 85 else 0.0 if m >= 60 else -100.0)  # continuous flooding keeps 10 cm
        notes = ["Alternate Wetting & Drying: re-flood to 5 cm when water drops 15 cm below soil "
                 "(keep 5 cm ponded during flowering). Saves ~25% water vs continuous flooding."]
        return dict(schedule=sched, notes=notes, initial_deficit=initial,
                    ratio_plan=round(sum(ks_plan) / len(ks_plan), 3),
                    ratio_none=round(sum(ks_none) / len(ks_none), 3))
