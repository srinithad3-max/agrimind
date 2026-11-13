"""
Orchestrator: runs the agent team over a shared blackboard and streams every
step (agent start, inter-agent messages, results) to the dashboard.

Data flow
  Farm context ─► crop.stage
  Weather ──────► weather.forecast ─┬─► Disease  (humidity → spread risk)
                                    ├─► Irrigation (rain, ET0)
  Disease ──────► disease.diagnosis ┼─► Irrigation (avoid wet leaves)
                                    └─► Yield (severity projection)
  Irrigation ───► irrigation.plan ──► Yield (water-stress factor)
  Yield ────────► yield.forecast ───► Advisory
  Advisory reads everything ────────► advisory.plan ─► Dashboard
"""
from __future__ import annotations

import time
import traceback
from datetime import date

from app.agents.advisory_agent import AdvisoryAgent
from app.agents.disease_agent import DiseaseAgent
from app.agents.irrigation_agent import IrrigationAgent
from app.agents.weather_agent import WeatherAgent
from app.agents.yield_agent import YieldAgent
from app.core.blackboard import Blackboard
from app.core.crops import crop, growth_stage

PIPELINE = [WeatherAgent, DiseaseAgent, IrrigationAgent, YieldAgent, AdvisoryAgent]


def agent_roster():
    return [dict(id=a.id, name=a.name, icon=a.icon, reads=a.reads, publishes=a.publishes) for a in PIPELINE]


def run_pipeline(ctx: dict, pace: float = 0.35):
    bb = Blackboard(ctx)
    t_start = time.time()
    yield dict(type="start", agents=agent_roster())

    stage = growth_stage(ctx["crop"], ctx["sowing_date"])
    bb.publish("crop.stage", stage, "orchestrator")
    c = crop(ctx["crop"])
    bb.message("orchestrator", f"New run: {c['name']}, {ctx['area']:g} acre(s) at {ctx['place']}. "
               f"Day {stage['das']} after sowing → stage '{stage['name']}' (Kc {stage['kc']:.2f}).")
    for e in bb.drain():
        yield e

    results = {"stage": stage}
    for cls in PIPELINE:
        agent = cls(bb)
        yield dict(type="agent_start", agent=agent.id)
        t0 = time.time()
        try:
            res = agent.run()
        except Exception as e:  # keep the demo alive and show what failed
            traceback.print_exc()
            bb.message(agent.id, f"Error: {type(e).__name__}: {e}", level="error")
            for evt in bb.drain():
                yield evt
            yield dict(type="error", agent=agent.id, error=str(e))
            return
        for evt in bb.drain():
            yield evt
            if evt["type"] == "message" and pace:
                time.sleep(pace)
        results[agent.id] = res
        yield dict(type="agent_done", agent=agent.id, ms=round((time.time() - t0) * 1000), output=res)

    results["log"] = bb.log
    results["runtime_ms"] = round((time.time() - t_start) * 1000)
    results["context"] = {k: (v.isoformat() if isinstance(v, date) else v)
                          for k, v in ctx.items() if k != "image"}
    yield dict(type="final", result=results)
