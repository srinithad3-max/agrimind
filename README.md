# 🌾 AgriMind: Multi-Agent AI Crop Intelligence (PS14)

Five cooperating AI agents (**Weather · Disease · Irrigation · Yield · Advisory**) share one *blackboard*,
talk to each other live on screen, and turn a leaf photo + soil card + live forecast into a
growth-stage-aware action plan in **English, Hindi and Telugu**, with voice, WhatsApp sharing and a printable report.

---

## 1. Run it (5 minutes)

```bash
cd agrimind
python -m venv .venv
# Windows: .venv\Scripts\activate      Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
#   (PyTorch is big. CPU-only version:  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu)
python run.py
```
Open **http://localhost:8000** · API docs at **http://localhost:8000/docs**

Works immediately, even before you train anything:
* Disease Agent uses OpenCV lesion analysis until `models/disease_model.pt` exists
* Yield model trains itself on first start (~10 s) → `models/yield_model.joblib`
* Weather is live from Open-Meteo (no key). If Wi-Fi fails, it uses the last cached forecast automatically.

## 2. Train the disease CNN (do this first tomorrow, runs while you do other things)

See the header of `training/train_disease.py`. Short version:
1. kaggle.com → New Notebook → Accelerator **GPU T4 x2** → Add Input **"New Plant Diseases Dataset"**
2. Upload `training/train_disease.py`, run
   `!python train_disease.py --data "<folder containing train/ and valid/>" --epochs 4`
3. Download `disease_model.pt`, `metrics.json`, `confusion_matrix.png`, `training_curves.png` → put in `models/`
4. Restart `python run.py`. The header pill turns green: **CNN ✓ … test acc 98.x%**, and Grad-CAM appears.

**Demo photos:** copy 3-4 leaf images from the dataset (e.g. `Tomato___Early_blight`, `Tomato___Late_blight`,
`Tomato___healthy`) into `samples/`, naming them like `tomato_early_blight.jpg`. They appear as one-click thumbnails, and
the "Tomato · blight" scenario auto-selects any file with *blight* in its name.
Also take 1-2 **real photos of leaves with your phone** for the "real-world" moment in the demo.

## 3. Optional: LLM (voice summary in Telugu/Hindi + "Ask AgriMind" chat)
Copy `.env.example` → `.env` and add a free Groq key (console.groq.com). Without it, everything still works with rule-based advice.

---

## 4. Architecture (put this on a slide)

```
 Leaf photo ─┐   Soil card ─┐   Location ─┐   Sowing date ─┐
             ▼              ▼             ▼                ▼
     ┌──────────────────── SHARED BLACKBOARD (facts + messages) ────────────────────┐
     │ crop.stage │ weather.forecast │ disease.diagnosis │ irrigation.plan │ yield… │
     └───▲──────────────▲──────────────────▲────────────────────▲─────────────▲─────┘
         │              │                  │                    │             │
   🌦 Weather      🔬 Disease         💧 Irrigation         📈 Yield      🧑‍🌾 Advisory
   Open-Meteo,     MobileNetV3 CNN,   FAO-56 soil-water     Gradient-      prioritises,
   ET₀, risk       Grad-CAM, OpenCV   balance, rain-aware,  boosted model, explains "why",
   flags           severity, spread   disease-aware method  3 scenarios,   EN/HI/TE, voice,
                   projection                               loss attribution WhatsApp
                                    ▼
                    Streaming dashboard (NDJSON, live agent conversation)
```

**How the agents actually cooperate (say these out loud):**
| From → To | What they exchange | Effect |
|---|---|---|
| Weather → Disease | humid / leaf-wetness days | disease spread projection speeds up |
| Weather → Irrigation | rain forecast, ET₀ | irrigation postponed / reduced before rain |
| Disease → Irrigation | "leaf-wetness pathogen" | switches sprinkler → drip, morning watering |
| Disease → Yield | projected severity, treated vs untreated | yield loss scenarios |
| Irrigation → Yield | water-stress factor with/without plan | yield loss scenarios |
| Weather → Advisory | dry window, rain timing | "spray TODAY before rain" vs "wait until Sat" |
| All → Advisory | everything | one ranked plan with reasons + ₹ value |

**Growth-stage awareness:** stage comes from days after sowing (FAO-56 stage lengths) and changes
Kc (water need), the irrigation trigger (stricter at flowering), heat-stress weight, disease-loss weight,
and the nutrient advice (N at vegetative, K at flowering, stop irrigation before harvest).

## 5. The 2-minute demo script

1. **Hook (15 s):** "India loses ~15-25% of crop output to pests and diseases, and farmers decide irrigation by guesswork.
   Meet Ramesh, 2 acres of tomato near Hyderabad, 80 days after sowing."
2. Click **Tomato · blight before rain** → **Run agent team**. *Stop talking and let them watch the agents talk.*
   Point at the arrows: "Weather just warned Irrigation about rain… Disease told Irrigation to stop the sprinkler."
3. **Disease card:** toggle *Photo → Lesion map → Grad-CAM*: "the model looks at the lesions, not the background."
4. **Action plan:** "Spray *today*, before Friday's rain. Irrigate 54 mm by drip, 66% less water."
   Switch to **తెలుగు**, press **🔊 Listen** and **💬 WhatsApp**.
5. **Money slide:** "No action → −33% yield. With AgriMind → −8%. That's ₹49,000 protected on 2 acres."
6. Switch to **Live · my farm**: real forecast right now → "this isn't scripted."

Always keep a **screen recording of a full run** ready in case the venue internet or laptop misbehaves.

## 6. Questions judges will ask (with answers)

* **"Isn't PlantVillage lab data?"** Yes, so we train with heavy augmentation (crop, rotation, blur, colour jitter),
  report a held-out test set, show low-confidence warnings ("retake photo"), and cross-check the plant species
  against the registered crop. Next step: fine-tune on field datasets like PlantDoc.
* **"Where does yield training data come from?"** An agronomic simulation built on published response curves
  (FAO-33 Ky water response, Mitscherlich nutrient response, temperature optima), learned by a gradient-boosting model
  (R² ≈ 0.97). `train_yield.py --csv` retrains on real field records with the same features. *Be honest about this; it
  earns respect.*
* **"Why is this multi-agent and not one script?"** Each agent owns one competence and publishes facts; others react to
  them (rain → irrigation postponed, pathogen → method changed). New agents (pest, market price, soil sensor) plug into
  the blackboard without touching the others.
* **"Why not just ask ChatGPT?"** The numbers come from models and FAO equations, not text generation. The LLM is
  optional and only rephrases and translates; the app runs fully offline without it.
* **"How would a farmer use it?"** A phone photo (the upload accepts the camera), a Telugu voice summary and WhatsApp
  sharing. The MobileNet model is also exported to ONNX for offline phone use.
* **"Scalability / future scope"** IoT soil-moisture sensors replace the slider, satellite NDVI, mandi price API,
  government scheme links (PM-KISAN, PMFBY), KVK expert escalation.

## 7. Project map
```
app/agents/      weather, disease, irrigation, yield, advisory agents
app/core/        blackboard, orchestrator, crop & disease knowledge bases, i18n, LLM
app/ml/          CNN + Grad-CAM, OpenCV severity, yield model
training/        train_disease.py (Kaggle GPU), train_yield.py
static/          dashboard (vanilla JS + SVG charts; no CDN needed)
models/          trained weights go here
samples/         demo leaf photos go here
```
Advice is decision support. Chemical doses must be confirmed on the product label and with the local KVK.
