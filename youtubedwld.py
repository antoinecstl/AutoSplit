import random
import string
from pytube import YouTube
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# URL de la vidéo YouTube à télécharger
video_url = 'https://www.youtube.com/watch?v=VEe4e0OA67I'

# Chemin local où enregistrer la vidéo
download_path = 'C:\\Users\\maxou\\OneDrive\\Documents'

# Authentification Google Drive
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Suivez les instructions pour autoriser l'accès à votre compte Google

# Création de l'objet GoogleDrive
drive = GoogleDrive(gauth)

# Téléchargement de la vidéo
yt = YouTube(video_url)
best_stream = yt.streams.get_highest_resolution()
video_extension = best_stream.mime_type.split('/')[-1]
random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
filename = f'video_{random_string}.{video_extension}'
video_path = f'{download_path}\\{filename}'
best_stream.download(output_path=download_path, filename=filename)

# Découpage de la vidéo en parties de 5 minutes
clip = VideoFileClip(video_path)
duration = clip.duration
part_duration = 3 * 60  # 5 minutes in seconds
num_parts = int(duration / part_duration) + 1

for i in range(num_parts):
    start_time = i * part_duration
    end_time = min((i + 1) * part_duration, duration)
    part_filename = f'part_{i + 1}_{random_string}.{video_extension}'
    part_path = f'{download_path}\\{part_filename}'
    subclip = clip.subclip(start_time, end_time)
    subclip.write_videofile(part_path, codec='libx264')


    # Chemin dans Google Drive où enregistrer la vidéo
    drive_folder_id = '1CZ8QHZ3WWuVYwfU0OZtFGGksUoBjAkEn'

    # Création d'un fichier dans Google Drive
    file_drive = drive.CreateFile({'title': part_filename, 'parents': [{'id': drive_folder_id}]})

    # Attachez le contenu du fichier local au fichier Google Drive
    file_drive.SetContentFile(part_path)

    # Téléversement du fichier vers Google Drive
    file_drive.Upload()


