import random
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

# Authentification
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Autoriser l'authentification via le navigateur

# Initialiser l'objet GoogleDrive
drive = GoogleDrive(gauth)

# ID du dossier "Vidéo_satisfaisante" dans Google Drive
folder_name = "Vidéo_satisfaisante"

# Rechercher le dossier par son nom
folder_query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
folder_list = drive.ListFile({'q': folder_query}).GetList()

if len(folder_list) == 1:
    selected_folder = folder_list[0]
    folder_id = selected_folder['id']

    # Récupérer la liste des vidéos non supprimées dans le dossier spécifié
    folder_query = f"'{folder_id}' in parents and mimeType contains 'video/' and trashed=false"
    folder_files = drive.ListFile({'q': folder_query}).GetList()

    if len(folder_files) > 0:
        # Choisir une vidéo au hasard
        random_video = random.choice(folder_files)

        # Spécifier le chemin de destination pour le téléchargement
        destination_folder = "C:\\Users\\maxou\\OneDrive\\Documents"

        # Créer le répertoire de destination s'il n'existe pas
        os.makedirs(destination_folder, exist_ok=True)

        # Nom de fichier local souhaité
        local_filename = "satisfaisant.mp4"

        # Télécharger la vidéo dans le répertoire de destination avec le nom souhaité
        destination_path = os.path.join(destination_folder, local_filename)
        random_video.GetContentFile(destination_path)
        print(f"Vidéo téléchargée avec succès sous le nom '{local_filename}'.")
    else:
        print("Aucune vidéo trouvée dans le dossier spécifié.")
else:
    print("Dossier spécifié non trouvé ou multiple dossiers trouvés.")
