"""Dataset preparation and optional custom YOLO training helpers."""

from __future__ import annotations

import shutil
import importlib
import sys
from pathlib import Path
from typing import Callable

from ...app_paths import get_yolo_models_root


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def prepare_nameplate_dataset(
    source_root: str,
    dataset_root: str,
    progress: Callable[[str], None] | None = None,
) -> tuple[int, int, int]:
    """Copy annotated learning images into a train/val YOLO dataset."""
    source = Path(source_root)
    dataset = Path(dataset_root)
    images = sorted(
        path for path in source.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        and path.with_suffix(".txt").is_file()
    )
    if len(images) < 2:
        raise ValueError("Cần ít nhất 2 ảnh có file .txt annotation để train.")

    for split in ("train", "val"):
        (dataset / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset / "labels" / split).mkdir(parents=True, exist_ok=True)

    val_count = max(1, round(len(images) * 0.2))
    train_count = 0
    copied_val = 0
    for index, image_path in enumerate(images):
        split = "val" if index % 5 == 0 and copied_val < val_count else "train"
        if split == "val":
            copied_val += 1
        else:
            train_count += 1
        shutil.copy2(image_path, dataset / "images" / split / image_path.name)
        shutil.copy2(image_path.with_suffix(".txt"), dataset / "labels" / split / f"{image_path.stem}.txt")

    yaml_path = dataset / "data.yaml"
    yaml_path.write_text(
        "path: %s\ntrain: images/train\nval: images/val\nnames:\n  0: nameplate\n"
        % str(dataset).replace("\\", "/"),
        encoding="utf-8",
    )
    if progress:
        progress(f"Dataset: {train_count} train, {copied_val} val, {len(images)} ảnh hợp lệ")
    return train_count, copied_val, len(images)


def train_nameplate_model(
    dataset_root: str,
    epochs: int = 100,
    progress: Callable[[str], None] | None = None,
) -> str:
    """Train nameplate and export the result to the runtime ONNX model path."""
    try:
        YOLO = _import_ultralytics().YOLO
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Thiếu ultralytics. Chạy: .venv\\Scripts\\python.exe -m pip install -r requirements-training.txt"
        ) from exc

    dataset = Path(dataset_root)
    run_root = Path(get_yolo_models_root()) / "training_runs"
    run_root.mkdir(parents=True, exist_ok=True)
    if progress:
        progress("Đang train nameplate trên CPU...")
    model = YOLO("yolo11n.pt")
    if progress:
        def on_epoch_end(trainer):
            progress(f"Train epoch {int(trainer.epoch) + 1}/{int(trainer.epochs)}")
        model.add_callback("on_fit_epoch_end", on_epoch_end)
    model.train(
        data=str(dataset / "data.yaml"),
        epochs=epochs,
        imgsz=640,
        batch=4,
        device="cpu",
        workers=0,
        project=str(run_root),
        name="nameplate",
        exist_ok=True,
    )

    best_pt = run_root / "nameplate" / "weights" / "best.pt"
    if not best_pt.is_file():
        raise RuntimeError(f"Không tìm thấy checkpoint sau khi train: {best_pt}")
    if progress:
        progress("Đang export model sang ONNX...")
    exported = YOLO(str(best_pt)).export(format="onnx", imgsz=640)
    exported_path = Path(str(exported))
    if not exported_path.is_file():
        raise RuntimeError(f"Không tìm thấy file ONNX sau khi export: {exported_path}")
    target = Path(get_yolo_models_root()) / "nameplate.onnx"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exported_path, target)
    return str(target)


def nameplate_model_needs_training(source_root: str) -> bool:
    """Return whether annotations are newer than the exported model."""
    model_path = Path(get_yolo_models_root()) / "nameplate.onnx"
    if not model_path.is_file():
        return True
    try:
        model_mtime = model_path.stat().st_mtime_ns
        suffixes = IMAGE_SUFFIXES | {".txt"}
        return any(
            path.stat().st_mtime_ns > model_mtime
            for path in Path(source_root).rglob("*")
            if path.is_file() and path.suffix.lower() in suffixes
        )
    except OSError:
        return True


def _import_ultralytics():
    """Import training dependency from the active interpreter or project venv."""
    try:
        return importlib.import_module("ultralytics")
    except ModuleNotFoundError as first_error:
        project_root = Path(__file__).resolve().parents[4]
        venv_site = project_root / ".venv" / "Lib" / "site-packages"
        if not venv_site.is_dir() or str(venv_site) in sys.path:
            raise first_error
        sys.path.insert(0, str(venv_site))
        importlib.invalidate_caches()
        return importlib.import_module("ultralytics")
