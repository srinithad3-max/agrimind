"""
Classical computer vision for leaf analysis (no deep learning needed).

1. Segment the leaf from the background (HSV + morphology + largest contour)
2. Split leaf pixels into healthy green tissue vs. lesion tissue
3. Severity = lesion area / leaf area  (standard plant-pathology metric)
4. Characterise the symptom by lesion colour: necrotic (brown/black),
   chlorotic (yellow), or powdery (white)

The CNN tells us WHICH disease; this module tells us HOW BAD it is.
"""
from __future__ import annotations

import base64

import cv2
import numpy as np


def _b64(img_bgr) -> str:
    ok, buf = cv2.imencode(".png", img_bgr)
    return "data:image/png;base64," + base64.b64encode(buf).decode()


def to_bgr(data: bytes):
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not read image")
    return img


def analyze_leaf(img_bgr) -> dict:
    h, w = img_bgr.shape[:2]
    scale = 320 / max(h, w)
    img = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)

    # ---- 1. leaf mask -----------------------------------------------------
    # Learn the background colour from the image border (plain paper, soil, table),
    # then keep pixels whose colour differs from it. Shadows are a darker version of
    # the background, so lightness differences count less than colour differences.
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    border = np.concatenate([lab[:6].reshape(-1, 3), lab[-6:].reshape(-1, 3),
                             lab[:, :6].reshape(-1, 3), lab[:, -6:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    d = lab - bg
    dist = np.sqrt((0.35 * d[..., 0]) ** 2 + d[..., 1] ** 2 + d[..., 2] ** 2)
    bdist = np.sqrt((0.35 * (border[:, 0] - bg[0])) ** 2 + (border[:, 1] - bg[1]) ** 2 + (border[:, 2] - bg[2]) ** 2)
    # robust to a leaf that touches the photo edge: use the typical border pixel, capped
    thr = float(np.clip(np.percentile(bdist, 60) + 8, 12, 26))
    bg_v = float(np.median(np.concatenate([V[:6].ravel(), V[-6:].ravel(), V[:, :6].ravel(), V[:, -6:].ravel()])))
    b, g, r = [img[..., i].astype(int) for i in range(3)]
    exg = 2 * g - r - b                                  # excess-green index
    # shadows: darker than the background but almost colourless
    chroma = np.sqrt(d[..., 1] ** 2 + d[..., 2] ** 2)
    Lc = lab[..., 0]
    texture = np.sqrt(np.maximum(cv2.blur(Lc * Lc, (9, 9)) - cv2.blur(Lc, (9, 9)) ** 2, 0))
    bg_tex = float(np.median(np.concatenate([texture[:8].ravel(), texture[-8:].ravel()])))
    # shadow = same hue as the background, darker, and as smooth as the background
    shadow = (chroma < 9) & (d[..., 0] < -6) & (exg < 15) & (texture < max(6.0, bg_tex * 2.2))
    seed = (((dist > thr) & ((S > 35) | (exg > 20))) | (dist > thr * 1.6)) & ~shadow | ((exg > 30) & (S > 40))
    # GrabCut refines the colour seed into a clean leaf outline (keeps dead brown tissue too)
    gc = np.full(S.shape, cv2.GC_PR_BGD, np.uint8)
    gc[seed] = cv2.GC_PR_FGD
    gc[(exg > 30) & (S > 50)] = cv2.GC_FGD
    edge = np.zeros(S.shape, bool)
    edge[:4, :] = edge[-4:, :] = edge[:, :4] = edge[:, -4:] = True
    gc[edge & ~seed] = cv2.GC_BGD                 # a leaf may touch the photo edge
    gc[shadow & (dist <= thr * 2)] = cv2.GC_BGD
    try:
        cv2.grabCut(img, gc, None, np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64),
                    4, cv2.GC_INIT_WITH_MASK)
        plant = np.isin(gc, (cv2.GC_FGD, cv2.GC_PR_FGD)) & ~shadow
    except cv2.error:
        plant = seed
    plant = plant.astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    plant = cv2.morphologyEx(plant, cv2.MORPH_OPEN, k)
    plant = cv2.morphologyEx(plant, cv2.MORPH_CLOSE, k, iterations=2)
    contours, _ = cv2.findContours(plant, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    leaf = np.zeros_like(plant)
    if contours:
        big = max(contours, key=cv2.contourArea)
        cv2.drawContours(leaf, [big], -1, 255, thickness=-1)   # fills holes (lesions)
    leaf[shadow] = 0
    leaf_px = int((leaf > 0).sum())
    if leaf_px < 0.05 * leaf.size:                      # segmentation failed -> whole image
        leaf[:] = 255
        leaf_px = leaf.size
        contours = []

    # ---- 2. healthy vs lesion --------------------------------------------
    inside = leaf > 0
    green = (H >= 25) & (H <= 95) & (S > 30) & (V > 30)          # includes dark/shaded green
    background_like = (dist <= thr) | shadow                      # holes cut in the leaf, shadow
    lesion = inside & ~green & ~background_like & ((S > 40) | (V < 80))
    lesion_u8 = cv2.morphologyEx(lesion.astype(np.uint8) * 255, cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    # ignore a thin rim at the leaf edge (shadow / background bleed)
    rim = cv2.erode(leaf, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    lesion = (lesion_u8 > 0) & (rim > 0)
    leaf_px = int((inside & ~background_like).sum()) or leaf_px
    lesion_px = int(lesion.sum())
    severity = lesion_px / max(1, leaf_px)

    # ---- 3. symptom type -------------------------------------------------
    yellow = lesion & (H >= 18) & (H < 30) & (S > 60)
    white = lesion & (S < 45) & (V > 160)
    necrotic = lesion & ~yellow & ~white
    parts = dict(necrotic_spots=int(necrotic.sum()), chlorosis=int(yellow.sum()), powdery=int(white.sum()))
    symptom = "healthy" if severity < 0.04 else max(parts, key=parts.get)
    n_spots = 0
    if lesion_px:
        n_spots, _ = cv2.connectedComponents(lesion.astype(np.uint8))
        n_spots -= 1

    # ---- 4. visual overlay ------------------------------------------------
    overlay = img.copy()
    tint = np.zeros_like(img)
    tint[necrotic] = (40, 40, 230)
    tint[yellow] = (0, 200, 255)
    tint[white] = (255, 120, 255)
    m = lesion
    overlay[m] = cv2.addWeighted(img, 0.35, tint, 0.65, 0)[m]
    outline, _ = cv2.findContours(leaf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, outline, -1, (90, 200, 90), 2)

    band = ("none" if severity < 0.04 else "low" if severity < 0.12
            else "moderate" if severity < 0.30 else "severe")
    return dict(
        severity=round(float(severity), 4), severity_band=band, symptom=symptom,
        lesion_count=int(n_spots), leaf_pixels=leaf_px,
        breakdown={k: round(v / max(1, leaf_px), 4) for k, v in parts.items()},
        overlay=_b64(overlay), original=_b64(img),
    )
