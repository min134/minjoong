"""TinyCNN 실습: python tinycnn.py / python tinycnn.py test / python tinycnn.py 사진.jpg"""

# ===== 학생이 바꾸는 설정: 처음에는 그대로 실행하세요. =====
EXPERIMENT = "baseline"  # 결과표에 남길 실험 이름
EPOCHS = 5             # 학습 반복 횟수 (두 배 비교: 10)
CHANNELS1 = 16          # 첫 번째 Conv 필터 수
CHANNELS2 = 32          # 두 번째 Conv 필터 수
HIDDEN = 64             # FC 은닉 노드 수 (비교: 16 또는 32)
TRAIN_SAMPLES = 10000   # 공식 학습 데이터의 앞 10,000장
BATCH_SIZE = 64         # 한 번에 학습하는 이미지 수
LEARNING_RATE = 0.001
# =======================================================

import csv
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import transforms
from torchvision.datasets import CIFAR10

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULT_DIR = ROOT / "results"
SEED = 20261110
THREADS = 2
CLASSES = ["airplane", "automobile", "bird", "cat", "deer",
           "dog", "frog", "horse", "ship", "truck"]
PREPROCESS = "rgb32_to_tensor_0to1_v1"


@dataclass
class ModelConfig:
    channels1: int = 16
    channels2: int = 32
    hidden: int = 64

    def __post_init__(self):
        if any(type(v) is not int or not 1 <= v <= 256 for v in asdict(self).values()):
            raise ValueError("필터 수와 FC 노드 수는 1~256 정수여야 합니다.")


class TinyCNN(nn.Module):
    """PDF의 Conv → Pool → Conv → Pool → FC → FC 구조."""
    def __init__(self, config=None):
        super().__init__()
        self.config = config or ModelConfig()
        c = self.config
        self.features = nn.Sequential(
            nn.Conv2d(3, c.channels1, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(c.channels1, c.channels2, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(c.channels2 * 8 * 8, c.hidden), nn.ReLU(),
            nn.Linear(c.hidden, 10),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


def image_transform(resize=False):
    # RGB 이미지를 0~1로 변환. PDF와 같이 Normalize는 사용하지 않는다.
    steps = [transforms.Resize((32, 32), antialias=True)] if resize else []
    return transforms.Compose([*steps, transforms.ToTensor()])


def train_epoch(model, loader, optimizer):
    model.train()
    loss_fn = nn.CrossEntropyLoss()
    loss_sum, samples = 0.0, 0
    for x, y in loader:
        optimizer.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        optimizer.step()
        loss_sum += loss.item() * len(y)
        samples += len(y)
    return loss_sum / samples


def evaluate(model, loader):
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for x, y in loader:
            correct += (model(x).argmax(dim=1) == y).sum().item()
            total += len(y)
    return correct, total


def save_result(model, result, history):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    # 새 번호를 배정하므로 같은 명령을 다시 실행해도 이전 모델을 보존한다.
    number = 1
    while True:
        path = RESULT_DIR / f"model_{number:06d}.pth"
        try:
            file = path.open("xb")
            break
        except FileExistsError:
            number += 1
    with file:
        torch.save({"format_version": 1, "model_config": asdict(model.config),
                    "state_dict": model.state_dict(), "preprocess": PREPROCESS,
                    "classes": CLASSES, "training": result, "history": history}, file)
    row = {"model_file": path.name, "experiment": result["experiment"],
           **result["model_config"],
           **{key: result[key] for key in ("epochs", "train_samples", "batch_size", "learning_rate",
                                           "parameters", "seed", "threads", "train_seconds", "test_seconds")},
           "test_samples": result["test_samples"], "correct": result["correct"],
           "test_accuracy_percent": 100 * result["test_accuracy"]}
    csv_path = RESULT_DIR / "results.csv"
    new_csv = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=row)
        if new_csv:
            writer.writeheader()
        writer.writerow(row)
    return path


def train():
    config = ModelConfig(CHANNELS1, CHANNELS2, HIDDEN)
    if any(type(v) is not int or v < 1 for v in (EPOCHS, BATCH_SIZE, TRAIN_SAMPLES)):
        raise ValueError("EPOCHS, BATCH_SIZE, TRAIN_SAMPLES는 1 이상의 정수여야 합니다.")
    if TRAIN_SAMPLES > 50000 or not 0 < LEARNING_RATE < 1:
        raise ValueError("TRAIN_SAMPLES는 최대 50,000, LEARNING_RATE는 0 초과 1 미만입니다.")
    torch.manual_seed(SEED)
    random.seed(SEED)
    print("데이터 준비 중 (첫 실행은 인터넷 연결과 다운로드 시간이 필요합니다)...", flush=True)
    train_full = CIFAR10(DATA_DIR, train=True, download=True, transform=image_transform())
    test_set = CIFAR10(DATA_DIR, train=False, download=True, transform=image_transform())
    train_set = Subset(train_full, range(TRAIN_SAMPLES))
    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True,
                              generator=torch.Generator().manual_seed(SEED), num_workers=0)
    test_loader = DataLoader(test_set, batch_size=256, shuffle=False, num_workers=0)
    model = TinyCNN(config).cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    parameters = sum(p.numel() for p in model.parameters())
    print(f"{EXPERIMENT} | CPU | 학습 {len(train_set):,}장 | batch {BATCH_SIZE} | {EPOCHS} epoch", flush=True)
    print(f"Conv {CHANNELS1}·{CHANNELS2} / FC {HIDDEN} | 파라미터 {parameters:,}개", flush=True)
    history = []
    start = time.perf_counter()
    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.perf_counter()
        loss = train_epoch(model, train_loader, optimizer)
        seconds = time.perf_counter() - epoch_start
        history.append({"epoch": epoch, "train_loss": loss, "train_seconds": seconds})
        print(f"Epoch {epoch:2d}/{EPOCHS} | loss={loss:.4f} | {seconds:.1f}초", flush=True)
    train_seconds = time.perf_counter() - start
    # 학습 종료 후 공식 test 전체 평가. 다운로드·평가 시간은 학습 시간과 분리한다.
    print("학습 완료. 테스트 10,000장 평가 중...", flush=True)
    test_start = time.perf_counter()
    correct, total = evaluate(model, test_loader)
    test_seconds = time.perf_counter() - test_start
    result = {"experiment": EXPERIMENT, "model_config": asdict(config), "parameters": parameters,
              "epochs": EPOCHS, "train_samples": len(train_set), "batch_size": BATCH_SIZE,
              "learning_rate": LEARNING_RATE, "seed": SEED, "threads": THREADS,
              "test_samples": total, "test_batch_size": 256, "correct": correct,
              "test_accuracy": correct / total, "train_seconds": train_seconds,
              "test_seconds": test_seconds, "preprocess": PREPROCESS, "torch_version": str(torch.__version__)}
    path = save_result(model, result, history)
    print(f"정확도: {100 * correct / total:.2f}% ({correct}/{total})", flush=True)
    print(f"학습: {train_seconds:.1f}초 (평균 {train_seconds / EPOCHS:.1f}초/epoch) | 테스트: {test_seconds:.1f}초")
    print(f"모델: {path}\n실험 비교표: {RESULT_DIR / 'results.csv'}")
    print("예측을 확인하려면: python tinycnn.py test")


def load_checkpoint(path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or checkpoint.get("format_version") != 1:
        raise ValueError("모델 형식이 다릅니다. 이 코드로 먼저 학습하세요.")
    if checkpoint.get("preprocess") != PREPROCESS or checkpoint.get("classes") != CLASSES:
        raise ValueError("모델의 전처리 또는 클래스 순서가 다릅니다.")
    # 현재 설정이 바뀌었더라도, 저장된 모델의 구조를 자동 복원한다.
    model = TinyCNN(ModelConfig(**checkpoint["model_config"]))
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    return model.eval(), checkpoint


def predict(image_path=None):
    paths = sorted(RESULT_DIR.glob("model_*.pth"))
    if not paths:
        raise FileNotFoundError("학습한 모델이 없습니다. python tinycnn.py를 먼저 실행하세요.")
    model, checkpoint = load_checkpoint(paths[-1])
    print(f"사용 모델: {paths[-1].name} | 구조: {checkpoint['model_config']}")
    with torch.no_grad():
        if image_path is not None:
            with Image.open(image_path) as image:
                x = image_transform(resize=True)(image.convert("RGB")).unsqueeze(0)
            print(f"예측: {CLASSES[model(x).argmax(dim=1).item()]}")
        else:
            # 별도 이미지 추출 파일 없이, 테스트 집합에서 클래스별 1장씩 보여준다.
            dataset = CIFAR10(DATA_DIR, train=False, download=True, transform=image_transform())
            print("정답          예측          결과 (클래스별 1장 예시이며 전체 정확도가 아닙니다)")
            for label, name in enumerate(CLASSES):
                x, _ = dataset[dataset.targets.index(label)]
                pred = model(x.unsqueeze(0)).argmax(dim=1).item()
                print(f"{name:12s}  {CLASSES[pred]:12s}  {'O' if pred == label else 'X'}")


def main():
    torch.set_num_threads(THREADS)
    args = sys.argv[1:]
    if not args:
        train()
    elif args == ["test"]:
        predict()
    elif len(args) == 1 and Path(args[0]).is_file():
        predict(args[0])
    elif args in (["--help"], ["-h"]):
        print(__doc__)
    else:
        raise ValueError("python tinycnn.py / python tinycnn.py test / python tinycnn.py 사진.jpg 중 하나로 실행하세요.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n실행을 중단했습니다. 이미 저장된 이전 실험은 results 폴더에 있습니다.")
        sys.exit(130)
    except (ValueError, FileNotFoundError) as error:
        print(f"오류: {error}", file=sys.stderr)
        sys.exit(1)
