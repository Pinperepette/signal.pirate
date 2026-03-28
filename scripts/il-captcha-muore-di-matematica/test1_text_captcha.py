"""
Test 1: Generare CAPTCHA testuali e romperli con una CNN
- Genera dataset sintetico di CAPTCHA con distorsione (multiprocessing)
- Addestra una CNN con multi-thread PyTorch
- Misura accuracy
"""

import os
import sys
import random
import string
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import torchvision.transforms as transforms
from multiprocessing import Pool, cpu_count
import time

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output_test1')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Config ---
CAPTCHA_LENGTH = 5
CHARS = string.ascii_uppercase + string.digits  # 36 classi
NUM_CLASSES = len(CHARS)
IMG_WIDTH = 160
IMG_HEIGHT = 60
TRAIN_SIZE = 50000
TEST_SIZE = 2000
EPOCHS = 40
BATCH_SIZE = 256
NUM_WORKERS = 16
DEVICE = torch.device('cpu')

# Sfrutta tutti i core per le operazioni PyTorch
torch.set_num_threads(24)
torch.set_num_interop_threads(8)

def log(msg):
    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()

log(f'Device: {DEVICE}')
log(f'CPU cores: {cpu_count()} — PyTorch threads: 24')
log(f'Caratteri: {NUM_CLASSES} classi, lunghezza CAPTCHA: {CAPTCHA_LENGTH}')
log(f'Dataset: {TRAIN_SIZE} train / {TEST_SIZE} test')

char_to_idx = {c: i for i, c in enumerate(CHARS)}
idx_to_char = {i: c for i, c in enumerate(CHARS)}


# --- Generatore CAPTCHA ---
def generate_captcha(text=None):
    """Genera un'immagine CAPTCHA con distorsione."""
    if text is None:
        text = ''.join(random.choices(CHARS, k=CAPTCHA_LENGTH))

    img = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 32)
    except:
        font = ImageFont.load_default()

    x_offset = 10
    for char in text:
        char_img = Image.new('RGBA', (35, 50), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        char_draw.text((5, 5), char, fill=color, font=font)
        angle = random.randint(-25, 25)
        char_img = char_img.rotate(angle, expand=False, fillcolor=(255, 255, 255, 0))
        img.paste(char_img, (x_offset, random.randint(-5, 10)), char_img)
        x_offset += 28

    for _ in range(random.randint(3, 6)):
        x1, y1 = random.randint(0, IMG_WIDTH), random.randint(0, IMG_HEIGHT)
        x2, y2 = random.randint(0, IMG_WIDTH), random.randint(0, IMG_HEIGHT)
        color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=random.randint(1, 2))

    for _ in range(200):
        x, y = random.randint(0, IMG_WIDTH - 1), random.randint(0, IMG_HEIGHT - 1)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.point((x, y), fill=color)

    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.0)))
    return img, text


def _generate_one(_):
    """Worker per multiprocessing."""
    img, text = generate_captcha()
    label = [char_to_idx[c] for c in text]
    # Converti in tensor subito per evitare di tenere PIL in memoria
    transform = transforms.ToTensor()
    img_t = transform(img)
    return img_t, label


def generate_dataset_parallel(size):
    """Genera dataset usando multiprocessing."""
    log(f'  Generazione {size} CAPTCHA con {NUM_WORKERS} worker...')
    t0 = time.time()
    with Pool(NUM_WORKERS) as pool:
        results = pool.map(_generate_one, range(size))
    elapsed = time.time() - t0
    log(f'  Generati in {elapsed:.1f}s ({size/elapsed:.0f} CAPTCHA/s)')
    return results


# --- Dataset ---
class CaptchaDataset(Dataset):
    def __init__(self, data):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        img_t, label = self.data[idx]
        return img_t, torch.tensor(label, dtype=torch.long)


# --- CNN ---
class CaptchaCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(128, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((2, 5)),
        )

        self.classifier = nn.Sequential(
            nn.Linear(256 * 2 * 5, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(1024, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
        )

        self.heads = nn.ModuleList([
            nn.Linear(512, NUM_CLASSES) for _ in range(CAPTCHA_LENGTH)
        ])

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return [head(x) for head in self.heads]


# --- Training ---
def train():
    log('\n[1/4] Generazione dataset...')
    train_data = generate_dataset_parallel(TRAIN_SIZE)
    test_data = generate_dataset_parallel(TEST_SIZE)

    train_dataset = CaptchaDataset(train_data)
    test_dataset = CaptchaDataset(test_data)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=NUM_WORKERS, pin_memory=True, persistent_workers=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE,
                             num_workers=4, pin_memory=True)

    # Salva qualche esempio
    log('\n[2/4] Salvataggio esempi...')
    for i in range(10):
        img, text = generate_captcha()
        img.save(os.path.join(OUTPUT_DIR, f'esempio_{i}_{text}.png'))

    log(f'\n[3/4] Training CNN — {EPOCHS} epoche, batch {BATCH_SIZE}...')
    model = CaptchaCNN().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    best_char_acc = 0
    t_start = time.time()

    for epoch in range(EPOCHS):
        t_epoch = time.time()
        model.train()
        total_loss = 0
        correct_chars = 0
        total_chars = 0

        for imgs, labels in train_loader:
            imgs = imgs.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(imgs)
            loss = sum(criterion(outputs[i], labels[:, i]) for i in range(CAPTCHA_LENGTH))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            for i in range(CAPTCHA_LENGTH):
                preds = outputs[i].argmax(dim=1)
                correct_chars += (preds == labels[:, i]).sum().item()
                total_chars += labels.size(0)

        scheduler.step()
        char_acc = correct_chars / total_chars * 100
        lr = optimizer.param_groups[0]['lr']
        elapsed = time.time() - t_epoch
        best_char_acc = max(best_char_acc, char_acc)

        log(f'  Epoch {epoch+1:2d}/{EPOCHS} — Loss: {total_loss/len(train_loader):.3f} — '
            f'Char acc: {char_acc:.1f}% — Best: {best_char_acc:.1f}% — '
            f'LR: {lr:.6f} — {elapsed:.1f}s')

    total_time = time.time() - t_start
    log(f'\n  Training completato in {total_time/60:.1f} minuti')

    # --- Test ---
    log(f'\n[4/4] Test...')
    model.eval()
    correct_captchas = 0
    correct_chars = 0
    total_chars = 0
    total_captchas = 0

    with torch.no_grad():
        for imgs, labels in test_loader:
            imgs = imgs.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(imgs)
            batch_all_correct = torch.ones(imgs.size(0), dtype=torch.bool, device=DEVICE)

            for i in range(CAPTCHA_LENGTH):
                preds = outputs[i].argmax(dim=1)
                correct_chars += (preds == labels[:, i]).sum().item()
                total_chars += labels.size(0)
                batch_all_correct &= (preds == labels[:, i])

            correct_captchas += batch_all_correct.sum().item()
            total_captchas += imgs.size(0)

    char_accuracy = correct_chars / total_chars * 100
    captcha_accuracy = correct_captchas / total_captchas * 100

    log(f'\n{"="*50}')
    log(f'RISULTATI TEST 1 — CAPTCHA TESTUALI')
    log(f'{"="*50}')
    log(f'Accuracy per carattere:  {char_accuracy:.1f}%')
    log(f'Accuracy CAPTCHA intero: {captcha_accuracy:.1f}%')
    log(f'(un CAPTCHA è corretto solo se TUTTI i {CAPTCHA_LENGTH} caratteri sono giusti)')
    log(f'Training: {TRAIN_SIZE} campioni, {EPOCHS} epoche, {total_time/60:.1f} min')
    log(f'{"="*50}')

    # Salva qualche predizione
    transform = transforms.ToTensor()
    log('\nEsempi di predizione:')
    with torch.no_grad():
        for i in range(20):
            img, text = generate_captcha()
            img_t = transform(img).unsqueeze(0).to(DEVICE)
            outputs = model(img_t)
            pred = ''.join(idx_to_char[o.argmax(dim=1).item()] for o in outputs)
            match = '✓' if pred == text else '✗'
            log(f'  Reale: {text} | Predetto: {pred} {match}')
            img.save(os.path.join(OUTPUT_DIR, f'pred_{i}_{text}_vs_{pred}.png'))

    # Salva il modello
    torch.save(model.state_dict(), os.path.join(OUTPUT_DIR, 'captcha_cnn.pt'))
    log(f'\nModello salvato in {OUTPUT_DIR}/captcha_cnn.pt')

    return char_accuracy, captcha_accuracy


if __name__ == '__main__':
    train()
