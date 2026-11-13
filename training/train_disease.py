"""
Train the AgriMind disease classifier (MobileNetV3-Large, transfer learning).

Run on a FREE GPU: Kaggle Notebook (recommended) or Google Colab.
------------------------------------------------------------------
KAGGLE (easiest, the dataset is already there):
  1. kaggle.com → Create → New Notebook → Settings → Accelerator: GPU T4 x2
  2. "+ Add Input" → search "New Plant Diseases Dataset" (vipoooool) → Add
  3. Upload this file (or paste it into a cell) and run:
       !python train_disease.py --data "/kaggle/input/new-plant-diseases-dataset/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)" --epochs 4
     (Folder names can differ slightly. Use the folder that contains train/ and valid/.)
  4. Download from the Output panel: disease_model.pt, metrics.json,
     confusion_matrix.png, training_curves.png. Put them in agrimind/models/.

Expected: ~97-99% validation accuracy in ~25-40 min on a T4.
Also works with the plain PlantVillage folder (class sub-folders, no split):
it then makes an 80/10/10 split itself.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchvision
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

p = argparse.ArgumentParser()
p.add_argument("--data", required=True, help="folder with train/ & valid/ OR class folders")
p.add_argument("--epochs", type=int, default=4)
p.add_argument("--bs", type=int, default=64)
p.add_argument("--lr", type=float, default=1e-3)
p.add_argument("--size", type=int, default=224)
p.add_argument("--arch", default="mobilenet_v3_large", choices=["mobilenet_v3_large", "efficientnet_b0"])
p.add_argument("--out", default=".")
p.add_argument("--max_per_class", type=int, default=0, help="cap images per class for a quick run (0 = all)")
args = p.parse_args()

dev = "cuda" if torch.cuda.is_available() else "cpu"
print("device:", dev)
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

# Strong augmentation so the model copes with real field photos, not just lab images
train_tf = transforms.Compose([
    transforms.RandomResizedCrop(args.size, scale=(0.6, 1.0)),
    transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(),
    transforms.RandomRotation(25),
    transforms.ColorJitter(0.35, 0.35, 0.3, 0.04),
    transforms.RandomApply([transforms.GaussianBlur(5)], p=0.2),
    transforms.ToTensor(), transforms.Normalize(MEAN, STD),
])
eval_tf = transforms.Compose([transforms.Resize((args.size, args.size)), transforms.ToTensor(),
                              transforms.Normalize(MEAN, STD)])

root = Path(args.data)
if (root / "train").exists() and (root / "valid").exists():
    train_ds = datasets.ImageFolder(root / "train", train_tf)
    val_full = datasets.ImageFolder(root / "valid", eval_tf)
    idx = np.random.default_rng(0).permutation(len(val_full))
    half = len(idx) // 2
    val_ds, test_ds = Subset(val_full, idx[:half]), Subset(val_full, idx[half:])
    classes = train_ds.classes
else:
    full_t = datasets.ImageFolder(root, train_tf)
    full_e = datasets.ImageFolder(root, eval_tf)
    classes = full_t.classes
    idx = np.random.default_rng(0).permutation(len(full_t))
    a, b = int(0.8 * len(idx)), int(0.9 * len(idx))
    train_ds, val_ds, test_ds = Subset(full_t, idx[:a]), Subset(full_e, idx[a:b]), Subset(full_e, idx[b:])

if args.max_per_class:
    targets = np.array(train_ds.targets if hasattr(train_ds, "targets") else [train_ds.dataset.targets[i] for i in train_ds.indices])
    keep = np.concatenate([np.where(targets == c)[0][:args.max_per_class] for c in range(len(classes))])
    train_ds = Subset(train_ds, keep)

print(f"{len(classes)} classes | train {len(train_ds)} | val {len(val_ds)} | test {len(test_ds)}")
kw = dict(batch_size=args.bs, num_workers=4, pin_memory=True)
tl = DataLoader(train_ds, shuffle=True, **kw)
vl = DataLoader(val_ds, **kw)
te = DataLoader(test_ds, **kw)

if args.arch == "efficientnet_b0":
    model = torchvision.models.efficientnet_b0(weights="IMAGENET1K_V1")
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
else:
    model = torchvision.models.mobilenet_v3_large(weights="IMAGENET1K_V2")
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(classes))
model.to(dev)

opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=args.epochs * len(tl))
crit = nn.CrossEntropyLoss(label_smoothing=0.1)
scaler = torch.amp.GradScaler(enabled=dev == "cuda")


def evaluate(loader):
    model.eval()
    ys, ps = [], []
    with torch.no_grad(), torch.autocast(dev, enabled=dev == "cuda"):
        for x, y in loader:
            ps.append(model(x.to(dev)).argmax(1).cpu())
            ys.append(y)
    y, pr = torch.cat(ys).numpy(), torch.cat(ps).numpy()
    return (y == pr).mean(), y, pr


hist = []
best, best_state = 0.0, None
for ep in range(args.epochs):
    model.train()
    t0, tot, correct, loss_sum = time.time(), 0, 0, 0.0
    for x, y in tl:
        x, y = x.to(dev, non_blocking=True), y.to(dev, non_blocking=True)
        opt.zero_grad(set_to_none=True)
        with torch.autocast(dev, enabled=dev == "cuda"):
            out = model(x)
            loss = crit(out, y)
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
        sched.step()
        loss_sum += loss.item() * len(y)
        correct += (out.argmax(1) == y).sum().item()
        tot += len(y)
    va, _, _ = evaluate(vl)
    hist.append(dict(epoch=ep + 1, train_loss=loss_sum / tot, train_acc=correct / tot, val_acc=float(va)))
    print(f"epoch {ep + 1}: loss {loss_sum / tot:.4f} train_acc {correct / tot:.4f} val_acc {va:.4f} ({time.time() - t0:.0f}s)")
    if va > best:
        best, best_state = va, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

model.load_state_dict(best_state)
test_acc, y, pr = evaluate(te)
print(f"TEST accuracy: {test_acc:.4f}")

# ---- metrics, confusion matrix, curves (put these on your slides!) ----
from sklearn.metrics import classification_report, confusion_matrix, f1_score  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
metrics = dict(test_acc=float(test_acc), best_val_acc=float(best), macro_f1=float(f1_score(y, pr, average="macro")),
               n_train=len(train_ds), n_test=len(test_ds), arch=args.arch, epochs=args.epochs, history=hist,
               report=classification_report(y, pr, target_names=classes, output_dict=True, zero_division=0))
(out / "metrics.json").write_text(json.dumps(metrics, indent=2))

cm = confusion_matrix(y, pr, normalize="true")
fig, ax = plt.subplots(figsize=(14, 12))
ax.imshow(cm, cmap="Greens")
short = [c.replace("___", ": ").replace("_", " ")[:28] for c in classes]
ax.set_xticks(range(len(classes)), short, rotation=90, fontsize=7)
ax.set_yticks(range(len(classes)), short, fontsize=7)
ax.set_title(f"Confusion matrix (test acc {test_acc:.2%}, macro-F1 {metrics['macro_f1']:.3f})")
plt.tight_layout()
plt.savefig(out / "confusion_matrix.png", dpi=150)

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([h["epoch"] for h in hist], [h["train_acc"] for h in hist], "o-", label="train")
ax.plot([h["epoch"] for h in hist], [h["val_acc"] for h in hist], "o-", label="validation")
ax.set_xlabel("epoch"); ax.set_ylabel("accuracy"); ax.legend(); ax.grid(alpha=.3)
plt.tight_layout()
plt.savefig(out / "training_curves.png", dpi=150)

torch.save(dict(state_dict=model.state_dict(), classes=classes, arch=args.arch, img_size=args.size,
                metrics=dict(test_acc=float(test_acc), macro_f1=metrics["macro_f1"])),
           out / "disease_model.pt")
print("saved disease_model.pt, metrics.json, confusion_matrix.png, training_curves.png")

# Optional: ONNX export, the same model can run offline on a phone
try:
    torch.onnx.export(model.cpu().eval(), torch.randn(1, 3, args.size, args.size), out / "disease_model.onnx",
                      input_names=["image"], output_names=["logits"], opset_version=17)
    print("saved disease_model.onnx (mobile/offline deployment)")
except Exception as e:
    print("ONNX export skipped:", e)
