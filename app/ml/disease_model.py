"""
Deep-learning disease classifier (PyTorch) with Grad-CAM explainability.

The model is trained by training/train_disease.py (run it on Kaggle/Colab GPU)
and saved to models/disease_model.pt. If PyTorch or the weights are missing,
the app still runs: the Disease Agent falls back to the OpenCV pipeline.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import numpy as np

MODELS = Path(__file__).resolve().parents[2] / "models"

try:
    import torch
    import torch.nn as nn
    import torchvision
    from torchvision import transforms
    TORCH = True
except Exception:  # pragma: no cover
    TORCH = False


def build_model(arch: str, num_classes: int):
    if arch == "efficientnet_b0":
        m = torchvision.models.efficientnet_b0(weights=None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, num_classes)
    else:  # mobilenet_v3_large (default, phone-friendly)
        m = torchvision.models.mobilenet_v3_large(weights=None)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, num_classes)
    return m


class DiseaseModel:
    def __init__(self, path: Path = MODELS / "disease_model.pt"):
        self.ready = False
        self.info = "PyTorch not installed" if not TORCH else f"No weights at {path.name}"
        if not TORCH or not path.exists():
            return
        ckpt = torch.load(path, map_location="cpu")
        self.classes = ckpt["classes"]
        self.arch = ckpt.get("arch", "mobilenet_v3_large")
        self.size = ckpt.get("img_size", 224)
        self.metrics = ckpt.get("metrics", {})
        self.model = build_model(self.arch, len(self.classes))
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()
        self.tf = transforms.Compose([
            transforms.Resize((self.size, self.size)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        self.target_layer = self.model.features[-1]
        self.ready = True
        acc = self.metrics.get("test_acc")
        self.info = f"{self.arch}, {len(self.classes)} classes" + (f", test acc {acc:.1%}" if acc else "")

    def predict(self, pil_img, topk: int = 3) -> dict:
        """Returns top-k predictions and a Grad-CAM heat-map overlay."""
        img = pil_img.convert("RGB")
        x = self.tf(img).unsqueeze(0)
        acts, grads = {}, {}

        def fwd_hook(_, __, out):
            acts["a"] = out
            out.register_hook(lambda g: grads.__setitem__("g", g))

        h = self.target_layer.register_forward_hook(fwd_hook)
        with torch.enable_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, 1)[0]
            top = torch.topk(probs, topk)
            cls = int(top.indices[0])
            self.model.zero_grad()
            logits[0, cls].backward()
        h.remove()

        # Grad-CAM: weight each feature map by its average gradient
        a, g = acts["a"][0], grads["g"][0]
        w = g.mean(dim=(1, 2))
        cam = torch.relu((w[:, None, None] * a).sum(0)).detach().numpy()
        cam = cam / (cam.max() + 1e-8)
        return dict(
            top=[dict(label=self.classes[int(i)], prob=float(p)) for p, i in zip(top.values, top.indices)],
            gradcam=self._overlay(img, cam),
        )

    @staticmethod
    def _overlay(pil_img, cam) -> str:
        import cv2
        rgb = np.array(pil_img.resize((320, 320)))
        heat = cv2.resize(cam, (320, 320))
        heat = cv2.applyColorMap(np.uint8(255 * heat), cv2.COLORMAP_JET)
        blend = cv2.addWeighted(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), 0.55, heat, 0.45, 0)
        ok, buf = cv2.imencode(".png", blend)
        return "data:image/png;base64," + base64.b64encode(buf).decode()


_model = None


def get_model() -> "DiseaseModel":
    global _model
    if _model is None:
        _model = DiseaseModel()
    return _model


def pil_from_bytes(data: bytes):
    from PIL import Image
    return Image.open(io.BytesIO(data))
