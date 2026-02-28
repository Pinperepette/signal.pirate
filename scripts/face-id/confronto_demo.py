import face_recognition
import numpy as np
from scipy.spatial.distance import cosine

# Carica le foto
img_ufficio = face_recognition.load_image_file("foto_ufficio.jpg")
img_esterno = face_recognition.load_image_file("foto_esterno.jpg")
img_estraneo = face_recognition.load_image_file("foto_estraneo.jpg")

# Confronto: stessa persona, condizioni diverse
emb1 = face_recognition.face_encodings(img_ufficio)[0]
emb2 = face_recognition.face_encodings(img_esterno)[0]

dist_coseno = cosine(emb1, emb2)
similarita = 1 - dist_coseno
dist_euclidea = np.linalg.norm(emb1 - emb2)

print(f"Distanza coseno:   {dist_coseno:.6f}")    # 0.016023
print(f"Similarità coseno: {similarita:.6f}")    # 0.983977
print(f"Distanza euclidea: {dist_euclidea:.6f}")  # 0.347821
print(f"Verdetto: STESSA PERSONA (< 0.6)")

# Confronto: persona diversa
emb3 = face_recognition.face_encodings(img_estraneo)[0]

dist_diversa = np.linalg.norm(emb1 - emb3)
print(f"Distanza euclidea: {dist_diversa:.6f}")  # 0.891234
print(f"Verdetto: PERSONA DIVERSA (>= 0.6)")
