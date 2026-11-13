"""
Disease knowledge base for the 38 PlantVillage classes.

pathogen   : fungal | bacterial | viral | pest | oomycete | none
aggressive : 0-1, how fast / how much yield it can destroy if untreated
humid      : True if spread is driven by leaf wetness / high humidity
Treatments are common recommendations; always confirm doses with the local
KVK / agriculture officer and the product label.
"""
from __future__ import annotations

KB: dict[str, dict] = {
    # ---------------- Tomato ----------------
    "Tomato___Early_blight": dict(
        name="Early blight", pathogen="fungal", aggressive=0.55, humid=True,
        chemical="Mancozeb 75% WP (2.5 g/L) or Chlorothalonil; alternate with Azoxystrobin",
        organic="Remove infected lower leaves, spray Trichoderma / neem-based formulation",
        prevention="Mulch to stop soil splash, stake plants, rotate away from Solanaceae for 2 seasons"),
    "Tomato___Late_blight": dict(
        name="Late blight", pathogen="oomycete", aggressive=1.0, humid=True,
        chemical="Metalaxyl 8% + Mancozeb 64% WP (2.5 g/L) or Cymoxanil + Mancozeb",
        organic="Uproot and destroy badly infected plants immediately; copper oxychloride spray",
        prevention="Avoid overhead irrigation, keep wide spacing, use resistant varieties"),
    "Tomato___Bacterial_spot": dict(
        name="Bacterial spot", pathogen="bacterial", aggressive=0.5, humid=True,
        chemical="Copper oxychloride 50% WP (3 g/L) + Streptocycline (as per label)",
        organic="Remove spotted leaves, avoid working in wet fields",
        prevention="Use disease-free seed, drip irrigation, 2-year rotation"),
    "Tomato___Leaf_Mold": dict(
        name="Leaf mould", pathogen="fungal", aggressive=0.4, humid=True,
        chemical="Chlorothalonil or Mancozeb spray",
        organic="Improve ventilation, prune lower leaves",
        prevention="Reduce humidity in polyhouses, wider spacing"),
    "Tomato___Septoria_leaf_spot": dict(
        name="Septoria leaf spot", pathogen="fungal", aggressive=0.45, humid=True,
        chemical="Chlorothalonil or Mancozeb at 7-10 day interval",
        organic="Remove infected leaves and plant debris",
        prevention="Mulch, avoid overhead watering, rotation"),
    "Tomato___Spider_mites Two-spotted_spider_mite": dict(
        name="Two-spotted spider mite", pathogen="pest", aggressive=0.45, humid=False,
        chemical="Miticide such as Abamectin or Spiromesifen (as per label)",
        organic="Neem oil 3% spray, wash undersides of leaves with water",
        prevention="Mites thrive in hot, dry weather - avoid water stress and dust"),
    "Tomato___Target_Spot": dict(
        name="Target spot", pathogen="fungal", aggressive=0.45, humid=True,
        chemical="Azoxystrobin or Chlorothalonil",
        organic="Remove lower infected leaves, improve airflow",
        prevention="Crop rotation, avoid dense canopy"),
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": dict(
        name="Yellow leaf curl virus", pathogen="viral", aggressive=0.9, humid=False,
        chemical="No cure. Control whitefly vector with Imidacloprid / Thiamethoxam (as per label)",
        organic="Uproot infected plants, yellow sticky traps (10/acre), neem oil",
        prevention="Insect-proof nursery net, resistant hybrids, remove weed hosts"),
    "Tomato___Tomato_mosaic_virus": dict(
        name="Tomato mosaic virus", pathogen="viral", aggressive=0.7, humid=False,
        chemical="No cure - remove infected plants",
        organic="Disinfect tools, wash hands (virus spreads by touch)",
        prevention="Certified seed, avoid tobacco use near plants"),
    "Tomato___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),

    # ---------------- Potato ----------------
    "Potato___Early_blight": dict(
        name="Early blight", pathogen="fungal", aggressive=0.5, humid=True,
        chemical="Mancozeb 75% WP (2.5 g/L) or Chlorothalonil",
        organic="Remove infected foliage, balanced nitrogen",
        prevention="Rotation, certified seed tubers"),
    "Potato___Late_blight": dict(
        name="Late blight", pathogen="oomycete", aggressive=1.0, humid=True,
        chemical="Metalaxyl + Mancozeb or Cymoxanil + Mancozeb; repeat in 7 days if wet",
        organic="Destroy infected haulms, copper spray",
        prevention="Resistant varieties (e.g. Kufri series), avoid evening irrigation"),
    "Potato___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),

    # ---------------- Maize ----------------
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": dict(
        name="Gray leaf spot", pathogen="fungal", aggressive=0.6, humid=True,
        chemical="Azoxystrobin + Propiconazole",
        organic="Bury crop residue after harvest",
        prevention="Resistant hybrids, rotation with legumes"),
    "Corn_(maize)___Common_rust_": dict(
        name="Common rust", pathogen="fungal", aggressive=0.45, humid=True,
        chemical="Mancozeb or Propiconazole at first pustules",
        organic="Remove heavily infected leaves",
        prevention="Resistant hybrids, timely sowing"),
    "Corn_(maize)___Northern_Leaf_Blight": dict(
        name="Northern leaf blight", pathogen="fungal", aggressive=0.6, humid=True,
        chemical="Mancozeb or Azoxystrobin + Propiconazole",
        organic="Residue management, balanced fertilisation",
        prevention="Resistant hybrids, rotation"),
    "Corn_(maize)___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),

    # ---------------- Pepper ----------------
    "Pepper,_bell___Bacterial_spot": dict(
        name="Bacterial spot", pathogen="bacterial", aggressive=0.5, humid=True,
        chemical="Copper oxychloride + Streptocycline (as per label)",
        organic="Remove infected leaves, avoid overhead irrigation",
        prevention="Hot-water treated seed, rotation"),
    "Pepper,_bell___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),

    # ---------------- Fruit crops & others ----------------
    "Apple___Apple_scab": dict(name="Apple scab", pathogen="fungal", aggressive=0.5, humid=True,
        chemical="Captan or Myclobutanil", organic="Rake and destroy fallen leaves",
        prevention="Prune for airflow, resistant cultivars"),
    "Apple___Black_rot": dict(name="Black rot", pathogen="fungal", aggressive=0.5, humid=True,
        chemical="Captan", organic="Prune out cankers and mummified fruit",
        prevention="Orchard sanitation"),
    "Apple___Cedar_apple_rust": dict(name="Cedar apple rust", pathogen="fungal", aggressive=0.4, humid=True,
        chemical="Myclobutanil", organic="Remove nearby juniper hosts",
        prevention="Resistant cultivars"),
    "Apple___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
    "Blueberry___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
    "Cherry_(including_sour)___Powdery_mildew": dict(name="Powdery mildew", pathogen="fungal", aggressive=0.35, humid=False,
        chemical="Wettable sulphur or Hexaconazole", organic="Potassium bicarbonate spray",
        prevention="Prune for airflow"),
    "Cherry_(including_sour)___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
    "Grape___Black_rot": dict(name="Black rot", pathogen="fungal", aggressive=0.6, humid=True,
        chemical="Mancozeb or Myclobutanil", organic="Remove mummified berries",
        prevention="Canopy management"),
    "Grape___Esca_(Black_Measles)": dict(name="Esca (black measles)", pathogen="fungal", aggressive=0.6, humid=False,
        chemical="No effective spray - prune infected wood", organic="Protect pruning wounds",
        prevention="Prune in dry weather"),
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": dict(name="Leaf blight", pathogen="fungal", aggressive=0.45, humid=True,
        chemical="Copper oxychloride or Mancozeb", organic="Remove infected leaves",
        prevention="Good airflow"),
    "Grape___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
    "Orange___Haunglongbing_(Citrus_greening)": dict(name="Citrus greening (HLB)", pathogen="bacterial", aggressive=0.9, humid=False,
        chemical="No cure - control psyllid vector with Imidacloprid", organic="Remove infected trees",
        prevention="Certified disease-free saplings"),
    "Peach___Bacterial_spot": dict(name="Bacterial spot", pathogen="bacterial", aggressive=0.45, humid=True,
        chemical="Copper-based bactericide", organic="Prune infected twigs",
        prevention="Resistant varieties"),
    "Peach___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
    "Raspberry___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
    "Soybean___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
    "Squash___Powdery_mildew": dict(name="Powdery mildew", pathogen="fungal", aggressive=0.4, humid=False,
        chemical="Wettable sulphur (2 g/L) or Hexaconazole", organic="Potassium bicarbonate / milk spray",
        prevention="Resistant varieties, sun exposure"),
    "Strawberry___Leaf_scorch": dict(name="Leaf scorch", pathogen="fungal", aggressive=0.4, humid=True,
        chemical="Captan", organic="Remove infected leaves",
        prevention="Renovate beds, drip irrigation"),
    "Strawberry___healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
}

# Used when the CNN is not available and the OpenCV fallback only knows the symptom type
SYMPTOM_FALLBACK = {
    "necrotic_spots": dict(name="Leaf spot / blight (suspected)", pathogen="fungal", aggressive=0.55, humid=True,
        chemical="Broad-spectrum protectant: Mancozeb 75% WP (2.5 g/L)",
        organic="Remove infected leaves, neem-based spray",
        prevention="Avoid leaf wetness, rotate crops"),
    "chlorosis": dict(name="Yellowing - virus / nutrient deficiency (suspected)", pathogen="viral", aggressive=0.5, humid=False,
        chemical="Check for whitefly/aphid vectors; soil-test for N / Mg deficiency",
        organic="Yellow sticky traps, foliar micronutrient spray",
        prevention="Vector control, balanced fertilisation"),
    "powdery": dict(name="Powdery mildew (suspected)", pathogen="fungal", aggressive=0.4, humid=False,
        chemical="Wettable sulphur (2 g/L)", organic="Potassium bicarbonate spray",
        prevention="Improve airflow and sunlight"),
    "healthy": dict(name="Healthy", pathogen="none", aggressive=0.0, humid=False),
}


def lookup(label: str) -> dict:
    info = KB.get(label)
    if info is None:
        healthy = "healthy" in label.lower()
        info = dict(name=label.split("___")[-1].replace("_", " "), pathogen="none" if healthy else "fungal",
                    aggressive=0.0 if healthy else 0.5, humid=not healthy)
    out = dict(info)
    out.setdefault("chemical", "")
    out.setdefault("organic", "")
    out.setdefault("prevention", "")
    out["plant"] = label.split("___")[0] if "___" in label else None
    out["healthy"] = out["pathogen"] == "none"
    return out


def pretty_plant(pv_name: str | None) -> str:
    if not pv_name:
        return "Unknown"
    return (pv_name.replace("_(maize)", "").replace("_(including_sour)", "")
            .replace(",_bell", " (bell)").replace("_", " "))
