import face_recognition
import numpy as np
from scipy.spatial.distance import cosine

# Carica la foto e estrai l'embedding 128D
img = face_recognition.load_image_file("faccia_mia.jpg")
encodings = face_recognition.face_encodings(img)

embedding = encodings[0]  # numpy array di 128 float

print(f"Dimensioni: {embedding.shape[0]}D")
print(f"Norma: {np.linalg.norm(embedding):.4f}")
print(f"Primi 8 valori:")
print(embedding[:8])

# Output:
# Dimensioni: 128D
# Norma: 1.0247
# Primi 8 valori:
# [-0.1530  0.0359  0.0332  0.0649 -0.1359 -0.0537  0.0579 -0.1235]
