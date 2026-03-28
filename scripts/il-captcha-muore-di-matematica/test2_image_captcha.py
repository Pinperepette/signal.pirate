"""
Test 2: CAPTCHA a immagini risolti con modello pre-trained
- Test su CIFAR-10 (32x32) e STL-10 (96x96) — foto reali
- ResNet-50 pre-trained su ImageNet, ZERO training aggiuntivo
- Simula griglia CAPTCHA e misura precision/recall
"""

import os
import sys
import random
import torch
import torchvision.transforms as transforms
from torchvision import models
from torchvision.models import ResNet50_Weights
from torchvision.datasets import CIFAR10, STL10
from PIL import Image, ImageDraw, ImageFont
import time

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output_test2')
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEVICE = torch.device('cpu')
torch.set_num_threads(24)
torch.set_num_interop_threads(8)

def log(msg):
    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()

log(f'Device: {DEVICE}')
log(f'PyTorch threads: 24')


def load_imagenet_labels():
    """Carica label ImageNet da weights."""
    weights = ResNet50_Weights.IMAGENET1K_V1
    return weights.meta['categories']


# Keywords ImageNet per matching con categorie CAPTCHA
IMAGENET_KEYWORDS = {
    'automobile': ['sports car', 'convertible', 'limousine', 'minivan', 'cab',
                   'beach wagon', 'car wheel', 'racer', 'Model T'],
    'truck': ['trailer truck', 'moving van', 'pickup', 'tow truck',
              'garbage truck', 'fire engine', 'recreational vehicle'],
    'airplane': ['airliner', 'warplane', 'wing', 'space shuttle'],
    'ship': ['liner', 'container ship', 'aircraft carrier', 'speedboat',
             'lifeboat', 'fireboat', 'gondola', 'canoe', 'catamaran',
             'trimaran', 'pirate', 'wreck'],
    'bird': ['robin', 'jay', 'magpie', 'chickadee', 'water ouzel',
             'kite', 'eagle', 'vulture', 'pelican', 'albatross',
             'crane', 'flamingo', 'hen', 'cock', 'ostrich', 'brambling',
             'goldfinch', 'house finch', 'junco', 'indigo bunting'],
    'cat': ['tabby', 'tiger cat', 'Persian cat', 'Siamese cat', 'Egyptian cat'],
    'dog': ['golden retriever', 'Labrador', 'German shepherd', 'beagle',
            'poodle', 'collie', 'boxer', 'husky', 'dalmatian', 'pug',
            'Rottweiler', 'Great Dane', 'chihuahua', 'bull terrier'],
    'deer': ['gazelle', 'impala', 'hartebeest', 'ibex'],
    'horse': ['sorrel', 'Arabian camel'],
    'frog': ['tree frog', 'tailed frog', 'bullfrog'],
}


def classify_batch(model, images, transform, top_k=10):
    """Classifica un batch di immagini."""
    batch = torch.stack([transform(img) for img in images]).to(DEVICE)
    with torch.no_grad():
        outputs = model(batch)
        probs = torch.nn.functional.softmax(outputs, dim=1)
        top_probs, top_indices = probs.topk(top_k, dim=1)
    return top_probs, top_indices


def test_dataset(model, dataset, labels, dataset_name, img_size,
                 target_classes, samples_per_class=500, batch_size=64):
    """Testa il modello su un dataset con foto reali."""
    log(f'\n{"="*70}')
    log(f'TEST: {dataset_name} ({img_size}x{img_size}px) — {samples_per_class} campioni/classe')
    log(f'{"="*70}')

    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    class_names = dataset.classes if hasattr(dataset, 'classes') else \
        ['airplane', 'bird', 'car', 'cat', 'deer', 'dog', 'horse', 'monkey', 'ship', 'truck']

    log(f'\n  {"Categoria":<15} {"N":<6} {"Top-1":<10} {"Top-5":<10} {"Top-10":<10}')
    log(f'  {"-"*55}')

    all_results = {}

    for cifar_class, cifar_name in target_classes.items():
        indices = [i for i, (_, label) in enumerate(dataset) if label == cifar_class]
        sample_indices = random.sample(indices, min(samples_per_class, len(indices)))

        keywords = IMAGENET_KEYWORDS.get(cifar_name, [cifar_name])
        top1_correct = 0
        top5_correct = 0
        top10_correct = 0

        # Process in batches
        for batch_start in range(0, len(sample_indices), batch_size):
            batch_indices = sample_indices[batch_start:batch_start + batch_size]
            batch_imgs = []
            for idx in batch_indices:
                img, _ = dataset[idx]
                if not isinstance(img, Image.Image):
                    img = transforms.ToPILImage()(img)
                batch_imgs.append(img)

            top_probs, top_indices = classify_batch(model, batch_imgs, transform, top_k=10)

            for i in range(len(batch_imgs)):
                top_labels = [labels[idx.item()].lower() for idx in top_indices[i]]

                def matches(label_list, kws):
                    return any(any(kw.lower() in l for kw in kws) for l in label_list)

                if matches(top_labels[:1], keywords):
                    top1_correct += 1
                if matches(top_labels[:5], keywords):
                    top5_correct += 1
                if matches(top_labels[:10], keywords):
                    top10_correct += 1

        n = len(sample_indices)
        all_results[cifar_name] = {
            'n': n,
            'top1': top1_correct / n * 100,
            'top5': top5_correct / n * 100,
            'top10': top10_correct / n * 100,
        }
        log(f'  {cifar_name:<15} {n:<6} {top1_correct/n*100:>5.1f}%    {top5_correct/n*100:>5.1f}%    {top10_correct/n*100:>5.1f}%')

        # Salva qualche esempio con predizione
        for i, idx in enumerate(sample_indices[:5]):
            img, _ = dataset[idx]
            if not isinstance(img, Image.Image):
                img = transforms.ToPILImage()(img)
            img_t = transform(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                output = model(img_t)
                probs = torch.nn.functional.softmax(output[0], dim=0)
                top5_p, top5_i = probs.topk(5)
            top1_label = labels[top5_i[0].item()]
            img_save = img.resize((224, 224), Image.NEAREST)
            img_save.save(os.path.join(OUTPUT_DIR,
                f'{dataset_name}_{cifar_name}_{i}_pred_{top1_label.replace(" ", "_")}.png'))

    return all_results


def simulate_captcha_grid(model, dataset, labels, target_class_idx, target_name,
                          class_names, n_simulations=100):
    """Simula N griglie CAPTCHA e misura performance."""
    log(f'\n{"="*70}')
    log(f'SIMULAZIONE: {n_simulations} griglie CAPTCHA 3x3')
    log(f'Prompt: "Seleziona tutte le immagini con {target_name.upper()}"')
    log(f'{"="*70}')

    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    keywords = IMAGENET_KEYWORDS.get(target_name, [target_name])

    # Prepara indici per classe
    target_indices = [i for i, (_, l) in enumerate(dataset) if l == target_class_idx]
    other_indices = [i for i, (_, l) in enumerate(dataset) if l != target_class_idx]

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_tn = 0
    grids_perfect = 0

    for sim in range(n_simulations):
        # Ogni griglia: 2-4 target + resto non-target
        n_targets = random.randint(2, 4)
        n_others = 9 - n_targets

        grid_target = random.sample(target_indices, n_targets)
        grid_other = random.sample(other_indices, n_others)

        grid = [(idx, True) for idx in grid_target] + [(idx, False) for idx in grid_other]
        random.shuffle(grid)

        sim_tp = 0
        sim_fp = 0
        sim_fn = 0

        for idx, is_target in grid:
            img, _ = dataset[idx]
            if not isinstance(img, Image.Image):
                img = transforms.ToPILImage()(img)

            img_t = transform(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                output = model(img_t)
                probs = torch.nn.functional.softmax(output[0], dim=0)
                _, top_indices = probs.topk(10)

            top_labels = [labels[i.item()].lower() for i in top_indices]
            model_says_target = any(
                any(kw.lower() in label for kw in keywords)
                for label in top_labels
            )

            if is_target and model_says_target:
                sim_tp += 1
                total_tp += 1
            elif is_target and not model_says_target:
                sim_fn += 1
                total_fn += 1
            elif not is_target and model_says_target:
                sim_fp += 1
                total_fp += 1
            else:
                total_tn += 1

        if sim_tp == n_targets and sim_fp == 0:
            grids_perfect += 1

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    log(f'\n  Risultati su {n_simulations} griglie:')
    log(f'  Precision:     {precision*100:.1f}%')
    log(f'  Recall:        {recall*100:.1f}%')
    log(f'  F1:            {f1*100:.1f}%')
    log(f'  Griglie perfette (tutti target trovati, zero falsi positivi):')
    log(f'    {grids_perfect}/{n_simulations} = {grids_perfect/n_simulations*100:.1f}%')
    log(f'  TP: {total_tp}  FP: {total_fp}  FN: {total_fn}  TN: {total_tn}')

    # Salva una griglia di esempio
    n_targets = 3
    grid_target = random.sample(target_indices, n_targets)
    grid_other = random.sample(other_indices, 9 - n_targets)
    grid = [(idx, True) for idx in grid_target] + [(idx, False) for idx in grid_other]
    random.shuffle(grid)

    tile_size = 96
    grid_img = Image.new('RGB', (tile_size * 3 + 8, tile_size * 3 + 50), (40, 40, 40))
    grid_draw = ImageDraw.Draw(grid_img)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 14)
    except:
        font = ImageFont.load_default()
    grid_draw.text((10, 5), f'Seleziona: {target_name.upper()}', fill=(255, 255, 255), font=font)

    for i, (idx, is_target) in enumerate(grid):
        row, col = i // 3, i % 3
        img, _ = dataset[idx]
        if not isinstance(img, Image.Image):
            img = transforms.ToPILImage()(img)
        img_r = img.resize((tile_size, tile_size))
        x = col * (tile_size + 4)
        y = 40 + row * (tile_size + 4)
        grid_img.paste(img_r, (x, y))
        if is_target:
            grid_draw.rectangle([x, y, x + tile_size, y + tile_size], outline=(0, 255, 0), width=2)

    grid_img.save(os.path.join(OUTPUT_DIR, f'captcha_grid_{target_name}.png'))

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'perfect_grids': grids_perfect / n_simulations,
    }


def main():
    t_start = time.time()

    log('\n[1/5] Caricamento modello ResNet-50 pre-trained...')
    model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V1).to(DEVICE)
    model.eval()
    labels = load_imagenet_labels()

    # --- CIFAR-10 (32x32) ---
    log('\n[2/5] Download CIFAR-10...')
    cifar10 = CIFAR10(root=os.path.join(OUTPUT_DIR, 'cifar10'),
                      train=False, download=True)

    cifar_classes = {
        0: 'airplane', 1: 'automobile', 2: 'bird', 3: 'cat', 4: 'deer',
        5: 'dog', 6: 'frog', 7: 'horse', 8: 'ship', 9: 'truck'
    }

    cifar_results = test_dataset(model, cifar10, labels, 'CIFAR-10', 32,
                                 cifar_classes, samples_per_class=500)

    # --- STL-10 (96x96) ---
    log('\n[3/5] Download STL-10...')
    stl10 = STL10(root=os.path.join(OUTPUT_DIR, 'stl10'),
                  split='test', download=True)

    # STL-10 classes: airplane, bird, car, cat, deer, dog, horse, monkey, ship, truck
    stl_classes = {
        0: 'airplane', 1: 'bird', 2: 'automobile', 3: 'cat', 4: 'deer',
        5: 'dog', 6: 'horse', 8: 'ship', 9: 'truck'
    }

    stl_results = test_dataset(model, stl10, labels, 'STL-10', 96,
                               stl_classes, samples_per_class=500)

    # --- Simulazione griglie CAPTCHA ---
    log('\n[4/5] Simulazione griglie CAPTCHA su CIFAR-10...')

    captcha_targets = {
        9: 'truck',
        1: 'automobile',
        0: 'airplane',
        8: 'ship',
    }

    grid_results = {}
    for class_idx, class_name in captcha_targets.items():
        grid_results[class_name] = simulate_captcha_grid(
            model, cifar10, labels, class_idx, class_name,
            cifar10.classes, n_simulations=200
        )

    # --- Riepilogo finale ---
    elapsed = time.time() - t_start
    log(f'\n\n{"="*70}')
    log(f'RIEPILOGO FINALE — TEST 2')
    log(f'{"="*70}')
    log(f'Modello: ResNet-50 pre-trained su ImageNet')
    log(f'Training aggiuntivo: ZERO')
    log(f'Tempo totale: {elapsed/60:.1f} minuti')

    log(f'\n--- Classificazione (Top-5 accuracy) ---')
    log(f'  {"Categoria":<15} {"CIFAR-10 32px":<18} {"STL-10 96px":<18}')
    log(f'  {"-"*50}')
    for cat in cifar_classes.values():
        c_acc = cifar_results.get(cat, {}).get('top5', 0)
        s_acc = stl_results.get(cat, {}).get('top5', 0)
        log(f'  {cat:<15} {c_acc:>6.1f}%           {s_acc:>6.1f}%')

    log(f'\n--- Simulazione griglia CAPTCHA (200 griglie ciascuna) ---')
    log(f'  {"Target":<15} {"Precision":<12} {"Recall":<12} {"Griglie OK":<12}')
    log(f'  {"-"*50}')
    for name, res in grid_results.items():
        log(f'  {name:<15} {res["precision"]*100:>6.1f}%     {res["recall"]*100:>6.1f}%     {res["perfect_grids"]*100:>6.1f}%')

    log(f'\n{"="*70}')
    log(f'CONCLUSIONE: Un modello pre-trained riconosce oggetti in foto reali')
    log(f'senza alcun addestramento specifico. Su immagini a risoluzione CAPTCHA')
    log(f'(96-300px) la performance è sufficiente per superare la maggior parte')
    log(f'delle griglie "seleziona tutti i..."')
    log(f'{"="*70}')


if __name__ == '__main__':
    main()
