"""Chargement des artefacts avec TensorFlow / Keras et joblib.

Imports tardifs : ces bibliothèques ne sont installées que dans l'image IA
(``requirements-ia.txt``). Sans elles, chaque zone échoue avec une
``ImportError`` explicite et le cycle ne publie que la météo.
"""


def load_keras_model(path):
    from tensorflow.keras.models import load_model

    return load_model(path, compile=False)


def load_scaler(path):
    # Fichier pickle : n'est appelé qu'après vérification de l'empreinte
    # SHA-256 approuvée (``ArtifactLoader``).
    import joblib

    return joblib.load(path)
