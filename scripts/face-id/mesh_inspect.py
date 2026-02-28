#!/usr/bin/env python3
"""Ispeziona face_mesh.obj — la tua faccia in numeri."""
import numpy as np

path = "/Users/pinperepette/Desktop/face_mesh.obj"
vertices, faces = [], []

with open(path) as f:
    for line in f:
        if line.startswith("v "):
            vertices.append([float(x) for x in line.split()[1:]])
        elif line.startswith("f "):
            faces.append([int(x) for x in line.split()[1:]])

v = np.array(vertices)
f = np.array(faces)

# Offusca le coordinate reali — ruota + scala + offset casuali
# La struttura resta identica ma i numeri non sono i miei
np.random.seed(42)
rot_angle = np.random.uniform(0.3, 0.8)
cos_a, sin_a = np.cos(rot_angle), np.sin(rot_angle)
rot = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
v = v @ rot.T * np.random.uniform(0.85, 1.15, 3) + np.random.uniform(-0.01, 0.01, 3)
vertices = v.tolist()

G = "\033[32m"   # verde
C = "\033[36m"   # cyan
Y = "\033[33m"   # giallo
W = "\033[0m"    # reset
D = "\033[90m"   # grigio

print(f"""
{G}╔══════════════════════════════════════════════════════════╗
║  face_mesh.obj — LA MIA FACCIA IN TESTO PURO            ║
╚══════════════════════════════════════════════════════════╝{W}

{Y}STRUTTURA{W}
  Vertici (v):    {G}{len(vertices)}{W}
  Triangoli (f):  {G}{len(faces)}{W}
  Peso file:      {G}78 KB{W}

{Y}COORDINATE (metri){W}
  X  min: {C}{v[:,0].min():+.6f}{W}  max: {C}{v[:,0].max():+.6f}{W}  range: {C}{v[:,0].ptp():.6f}{W}
  Y  min: {C}{v[:,1].min():+.6f}{W}  max: {C}{v[:,1].max():+.6f}{W}  range: {C}{v[:,1].ptp():.6f}{W}
  Z  min: {C}{v[:,2].min():+.6f}{W}  max: {C}{v[:,2].max():+.6f}{W}  range: {C}{v[:,2].ptp():.6f}{W}

{Y}BOUNDING BOX{W}
  Larghezza volto:  {G}{v[:,0].ptp()*100:.1f} cm{W}
  Altezza volto:    {G}{v[:,1].ptp()*100:.1f} cm{W}
  Profondità volto: {G}{v[:,2].ptp()*100:.1f} cm{W}

{Y}PRIMI 10 VERTICI{W} {D}(x, y, z in metri){W}""")

for i in range(10):
    x, y, z = vertices[i]
    print(f"  v[{i:4d}]  {C}{x:+.6f}  {y:+.6f}  {z:+.6f}{W}")

print(f"  {D}...{W}")
print(f"  v[{len(vertices)-1:4d}]  {C}{vertices[-1][0]:+.6f}  {vertices[-1][1]:+.6f}  {vertices[-1][2]:+.6f}{W}")

print(f"""
{Y}PRIMI 10 TRIANGOLI{W} {D}(indici vertici){W}""")

for i in range(10):
    a, b, c = faces[i]
    print(f"  f[{i:4d}]  {G}{a:5d}  {b:5d}  {c:5d}{W}")

print(f"  {D}...{W}")
print(f"  f[{len(faces)-1:4d}]  {G}{faces[-1][0]:5d}  {faces[-1][1]:5d}  {faces[-1][2]:5d}{W}")

# Punto più vicino alla camera (z max = naso)
nose = np.argmax(v[:, 2])
print(f"""
{Y}PUNTO PIÙ VICINO (NASO){W}
  v[{nose}]  {C}{v[nose][0]:+.6f}  {v[nose][1]:+.6f}  {v[nose][2]:+.6f}{W}

{G}La tua faccia pesa meno di un'icona del desktop.{W}
""")
