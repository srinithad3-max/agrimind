"""Built-in Hindi / Telugu translations for advisory headlines (works offline).
Full-text translation of details is done by the optional LLM (see app/core/llm.py)."""

T = {
    "spray_now": {
        "en": "Spray {product} today, before the rain",
        "hi": "बारिश से पहले आज ही {product} का छिड़काव करें",
        "te": "వర్షం రాకముందే ఈరోజే {product} పిచికారీ చేయండి",
    },
    "spray_soon": {
        "en": "Spray {product} within 24 hours",
        "hi": "24 घंटे के भीतर {product} का छिड़काव करें",
        "te": "24 గంటల్లోపు {product} పిచికారీ చేయండి",
    },
    "spray_after_rain": {
        "en": "Wait for the rain to pass, then spray on {day}",
        "hi": "बारिश रुकने तक रुकें, फिर {day} को छिड़काव करें",
        "te": "వర్షం తగ్గే వరకు ఆగి, {day} న పిచికారీ చేయండి",
    },
    "virus_remove": {
        "en": "Uproot infected plants and control the insect vector",
        "hi": "संक्रमित पौधे उखाड़ें और रोग फैलाने वाले कीटों को नियंत्रित करें",
        "te": "వ్యాధి సోకిన మొక్కలను పీకేసి, వ్యాధిని వ్యాపింపజేసే పురుగులను నియంత్రించండి",
    },
    "preventive_spray": {
        "en": "High fungal risk: preventive protectant spray recommended",
        "hi": "फफूंद रोग का खतरा अधिक: बचाव के लिए छिड़काव करें",
        "te": "శిలీంధ్ర వ్యాధి ప్రమాదం ఎక్కువ: ముందు జాగ్రత్తగా పిచికారీ చేయండి",
    },
    "scout": {
        "en": "Scout the field for disease this week",
        "hi": "इस सप्ताह खेत में रोग की जाँच करें",
        "te": "ఈ వారం పొలంలో వ్యాధి లక్షణాలు పరిశీలించండి",
    },
    "irrigate": {
        "en": "Irrigate {mm} mm on {days}",
        "hi": "{days} को {mm} मिमी सिंचाई करें",
        "te": "{days} న {mm} మి.మీ నీరు పెట్టండి",
    },
    "skip_irrigation": {
        "en": "Skip irrigation: {rain} mm rain expected this week",
        "hi": "सिंचाई न करें: इस सप्ताह {rain} मिमी बारिश की संभावना",
        "te": "నీరు పెట్టవద్దు: ఈ వారం {rain} మి.మీ వర్షం అంచనా",
    },
    "no_irrigation": {
        "en": "No irrigation needed this week",
        "hi": "इस सप्ताह सिंचाई की आवश्यकता नहीं",
        "te": "ఈ వారం నీరు పెట్టాల్సిన అవసరం లేదు",
    },
    "switch_drip": {
        "en": "Use drip, not {method}: keep leaves dry",
        "hi": "{method} के बजाय ड्रिप से सिंचाई करें: पत्तियाँ सूखी रखें",
        "te": "{method} బదులు డ్రిప్ వాడండి: ఆకులు తడవకుండా చూడండి",
    },
    "awd": {
        "en": "Use Alternate Wetting & Drying to save water",
        "hi": "पानी बचाने के लिए बारी-बारी से गीला-सूखा (AWD) तरीका अपनाएँ",
        "te": "నీటి ఆదా కోసం AWD (తడి-పొడి) పద్ధతి పాటించండి",
    },
    "heat": {
        "en": "Heat alert: {temp}°C on {day}",
        "hi": "गर्मी की चेतावनी: {day} को {temp}°C",
        "te": "వేడి హెచ్చరిక: {day} న {temp}°C",
    },
    "heavy_rain": {
        "en": "Heavy rain on {day}: clear drains, delay fertiliser",
        "hi": "{day} को भारी बारिश: नालियाँ साफ़ करें, खाद डालना टालें",
        "te": "{day} న భారీ వర్షం: కాలువలు శుభ్రం చేయండి, ఎరువు వేయడం వాయిదా వేయండి",
    },
    "nitrogen": {
        "en": "Top-dress nitrogen: soil N is limiting yield",
        "hi": "नाइट्रोजन की टॉप-ड्रेसिंग करें: मिट्टी में N की कमी उपज घटा रही है",
        "te": "నత్రజని పైపాటుగా వేయండి: నేలలో N లోపం దిగుబడి తగ్గిస్తోంది",
    },
    "potassium": {
        "en": "Apply potash to support flowering and fruit/grain fill",
        "hi": "फूल और दाना/फल भरने के लिए पोटाश दें",
        "te": "పూత మరియు గింజ/కాయ నిండడానికి పొటాష్ వేయండి",
    },
    "phosphorus": {
        "en": "Soil phosphorus is low: apply DAP/SSP",
        "hi": "मिट्टी में फॉस्फोरस कम है: DAP/SSP डालें",
        "te": "నేలలో భాస్వరం తక్కువ: DAP/SSP వేయండి",
    },
    "ph_acid": {
        "en": "Soil pH {ph} is too low for this crop: apply agricultural lime",
        "hi": "इस फसल के लिए मिट्टी का pH {ph} कम है: कृषि चूना डालें",
        "te": "ఈ పంటకు నేల pH {ph} తక్కువ: వ్యవసాయ సున్నం వేయండి",
    },
    "ph_alk": {
        "en": "Soil pH {ph} is too high for this crop: add gypsum and organic manure",
        "hi": "इस फसल के लिए मिट्टी का pH {ph} अधिक है: जिप्सम और जैविक खाद डालें",
        "te": "ఈ పంటకు నేల pH {ph} ఎక్కువ: జిప్సం, సేంద్రియ ఎరువు వేయండి",
    },
    "rotation": {
        "en": "Rotate crops: avoid the {family} family next season",
        "hi": "फसल चक्र अपनाएँ: अगले सीज़न {family} कुल की फसल न लगाएँ",
        "te": "పంట మార్పిడి చేయండి: వచ్చే సీజన్‌లో {family} కుటుంబ పంట వేయకండి",
    },
    "harvest": {
        "en": "Crop is maturing: stop irrigation and plan harvest on a dry day",
        "hi": "फसल पक रही है: सिंचाई रोकें और सूखे दिन कटाई करें",
        "te": "పంట కోతకు వస్తోంది: నీరు ఆపి, పొడి రోజున కోత ప్లాన్ చేయండి",
    },
    "healthy": {
        "en": "Crop looks healthy: keep monitoring",
        "hi": "फसल स्वस्थ दिख रही है: निगरानी जारी रखें",
        "te": "పంట ఆరోగ్యంగా ఉంది: పరిశీలన కొనసాగించండి",
    },
    "mismatch": {
        "en": "Photo looks like {img_crop}, not your crop: please re-check",
        "hi": "फोटो {img_crop} की लगती है, आपकी फसल की नहीं: दोबारा जाँचें",
        "te": "ఫోటో మీ పంటది కాదు, {img_crop} లా ఉంది: మళ్ళీ తనిఖీ చేయండి",
    },
    "yield_protect": {
        "en": "This plan protects about {q} quintals (₹{rs})",
        "hi": "यह योजना लगभग {q} क्विंटल (₹{rs}) उपज बचाती है",
        "te": "ఈ ప్రణాళిక సుమారు {q} క్వింటాళ్ళ (₹{rs}) దిగుబడిని కాపాడుతుంది",
    },
}

WEEKDAYS = {
    "hi": {"Mon": "सोम", "Tue": "मंगल", "Wed": "बुध", "Thu": "गुरु", "Fri": "शुक्र", "Sat": "शनि", "Sun": "रवि"},
    "te": {"Mon": "సోమ", "Tue": "మంగళ", "Wed": "బుధ", "Thu": "గురు", "Fri": "శుక్ర", "Sat": "శని", "Sun": "ఆది"},
}


def localize_day(s: str, lang: str) -> str:
    for en, loc in WEEKDAYS.get(lang, {}).items():
        s = s.replace(en, loc)
    return s


def render(key: str, params: dict, lang: str) -> str:
    tpl = T.get(key, {}).get(lang) or T.get(key, {}).get("en", key)
    p = {k: (localize_day(v, lang) if isinstance(v, str) else v) for k, v in params.items()}
    try:
        return tpl.format(**p)
    except Exception:
        return T.get(key, {}).get("en", key).format(**params)
