import os
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import random
import io
from googleapiclient.http import MediaIoBaseDownload


class GoogleDriveService:
    def __init__(self):
        self._SCOPES = ['https://www.googleapis.com/auth/drive']

        _base_path = os.path.dirname(__file__)
        _credential_path = os.path.join(_base_path, 'credential.json')
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _credential_path

    def build(self):
        creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), self._SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service

# Créer une instance du service Google Drive
drive_service = GoogleDriveService()
service = drive_service.build()

# ID du dossier "Vidéo_satisfaisante" dans Google Drive
folder_name = "Vidéo_satisfaisante"

# Rechercher le dossier par son nom
folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
folder_results = service.files().list(q=folder_query).execute()
folder_items = folder_results.get('files', [])

if len(folder_items) == 1:
    folder_id = folder_items[0]['id']

    # Récupérer la liste des vidéos non supprimées dans le dossier spécifié
    video_query = f"'{folder_id}' in parents and mimeType contains 'video/' and trashed=false"
    video_results = service.files().list(q=video_query).execute()
    video_items = video_results.get('files', [])

    if len(video_items) > 0:
        # Choisir une vidéo au hasard
        random_video = random.choice(video_items)

        # Télécharger la vidéo
        request = service.files().get_media(fileId=random_video['id'])
        fh = io.FileIO(random_video['satisfaisant.mp4'], 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        print(f"Vidéo téléchargée avec succès sous le nom '{random_video['name']}'.")
    else:
        print("Aucune vidéo trouvée dans le dossier spécifié.")
else:
    print("Dossier spécifié non trouvé ou plusieurs dossiers trouvés.")
