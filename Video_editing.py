from faster_whisper import WhisperModel
from moviepy.editor import TextClip, VideoFileClip, CompositeVideoClip, ColorClip, concatenate_videoclips
from pytube import YouTube
import matplotlib.pyplot as plt
import numpy as np
import ffmpeg
import requests
import json
import re
import os
import random
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import string

def get_video_duration(youtube_url):
    try:
        # Faire une requête HTTP GET vers la page YouTube
        response = requests.get(youtube_url)
        response.raise_for_status()  # Vérifier si la requête s'est déroulée sans erreur

        # Extraire le code HTML de la réponse
        html_code = response.text

        # Utiliser une expression régulière pour rechercher la durée de la vidéo
        duration_match = re.search(r'"approxDurationMs":"(\d+)"', html_code)

        if duration_match:
            # Convertir la durée en millisecondes en minutes
            duration_ms = int(duration_match.group(1))
            total_minutes = duration_ms // 1000

            # Retourner la durée de la vidéo en minutes
            return total_minutes
        else:
            print("Impossible de trouver la durée de la vidéo.")
            return None

    except requests.exceptions.RequestException as e:
        print("Une erreur s'est produite lors de la requête :", e)
        return None

def parse_coordinates(path_string):
    coords = []
    commands = path_string.split(" ")
    command_idx = 0
    x, y = 0, 0  # Starting point

    while command_idx < len(commands):
        command = commands[command_idx]

        if command == "M":  # Move to
            x, y = float(commands[command_idx + 1]), float(commands[command_idx + 2])
            coords.append((x, y))
            command_idx += 3

        elif command == "C":  # Cubic Bezier curve
            for i in range(0, 6, 2):
                x, y = float(commands[command_idx + i + 1]), float(commands[command_idx + i + 2])
                coords.append((x, y))
            command_idx += 7

        else:
            command_idx += 1

    return coords

def get_intervals65sec(video_duration, path_data):
    # Diviser les coordonnées x et y en listes séparées
    x_data, y_data = zip(*path_data)

    # Convertir les coordonnées x en minutes
    x_data_minutes = [x * video_duration / max(x_data) for x in x_data]

    # Trouver les indices triés des points bas par valeur y en ordre croissant
    sorted_indices = np.argsort(y_data)

    # Choisir les trois points bas avec les valeurs y les plus faibles, mais dont les coordonnées x sont éloignées d'au moins une minute l'une de l'autre et ne sont pas à 1 minute du début ou de la fin
    num_bottom_points = 6
    bottom_points_indices = []
    i = 0
    while len(bottom_points_indices) < num_bottom_points:
        index = sorted_indices[i]
        x_value = x_data_minutes[index]
        if not any(abs(x_value - x_data_minutes[index2]) < 65 for index2 in bottom_points_indices) and 65 < x_value < (video_duration - 65):
            bottom_points_indices.append(index)
        i += 1

    bottom_points_x = np.array(x_data_minutes)[bottom_points_indices]
    bottom_points_y = np.array(y_data)[bottom_points_indices]

    # Afficher les intervalles de 1min05 autour des points bas sous forme de barres verticales
    intervals = []
    for i in range(num_bottom_points):
        start_time = round(bottom_points_x[i] - 20, 0)
        end_time = round(bottom_points_x[i] + 45, 0)
        intervals.append((start_time, end_time))

    return intervals

def plot_svg_curve_with_intervals(video_url, path_string):
    # Obtenir la durée de la vidéo à partir du lien
    duration = get_video_duration(video_url)

    if duration:
        print("Durée de la vidéo :", duration)
    else:
        print("Impossible d'obtenir la durée de la vidéo. Veuillez vérifier le lien ou réessayer plus tard.")
        return

    # Les coordonnées du chemin SVG
    path_data = parse_coordinates(path_string)

    # Durée totale de la vidéo en minutes
    video_duration = duration

    # Diviser les coordonnées x et y en listes séparées
    x_data, y_data = zip(*path_data)

    # Convertir les coordonnées x en minutes
    x_data_minutes = [x * video_duration / max(x_data) for x in x_data]

    # Trouver les indices triés des points bas par valeur y en ordre croissant
    sorted_indices = np.argsort(y_data)

    # Choisir les trois points bas avec les valeurs y les plus faibles, mais dont les coordonnées x sont éloignées d'au moins une minute l'une de l'autre et ne sont pas à 1 minute du début ou de la fin
    num_bottom_points = 3
    bottom_points_indices = []
    i = 0
    while len(bottom_points_indices) < num_bottom_points:
        index = sorted_indices[i]
        x_value = x_data_minutes[index]
        if not any(abs(x_value - x_data_minutes[index2]) < 60 for index2 in bottom_points_indices) and 60 < x_value < (video_duration - 60):
            bottom_points_indices.append(index)
        i += 1

    bottom_points_x = np.array(x_data_minutes)[bottom_points_indices]
    bottom_points_y = np.array(y_data)[bottom_points_indices]

    # Tracer la courbe avec des points connectés par des lignes
    plt.plot(x_data_minutes, y_data, label='Courbe SVG')

    # Ajouter les points des pics les plus bas
    plt.scatter(bottom_points_x, bottom_points_y, color='green', label='Point bas')

    # Ajouter les légendes
    plt.legend()

    # Afficher les intervalles de 1min05 autour des points bas sous forme de barres verticales
    intervals = get_intervals65sec(video_duration, path_data)
    for interval in intervals:
        start_time, end_time = interval
        plt.axvspan(start_time, end_time, color='yellow', alpha=0.3)

    # Afficher les temps des points bas et leurs valeurs y correspondantes
    for x, y in zip(bottom_points_x, bottom_points_y):
        plt.annotate(f'({x:.2f}, {y:.2f})', xy=(x, y), xytext=(x, y+0.5), ha='center', fontsize=8, color='blue')

    print(intervals)

    # Afficher le graphique
    plt.xlabel('Temps (minutes)')
    plt.ylabel('Y')
    plt.title('Courbe SVG avec Points Bas et Intervalle de 1min05')
    plt.grid(True)
    plt.tight_layout()  # Pour éviter que le titre soit tronqué
    plt.show()

def download_youtube_video(video_url):
    try:
        # Créer une instance YouTube
        yt = YouTube(video_url)

        # Sélectionner le format de la vidéo à télécharger (format vidéo avec la meilleure qualité)
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()

        # Télécharger la vidéo dans le dossier de sortie spécifié
        print("Téléchargement en cours...")
        video_stream.download(filename="ytb_path.mp4")

        print("Téléchargement terminé !")
    except Exception as e:
        print(f"Une erreur s'est produite : {e}")


def overlay_videos(background_path, output_path, mp4videoURL="."):


    heatmap = 12

    while heatmap != 0 and heatmap != 1 :
        heatmap = int(input("Avez vous une Heatmap (1 = Oui, 0 = Non) : "))

    if heatmap == 1 :
        path_string = input("Entrez le SVG de la Heatmap : ")

        path_data = parse_coordinates(path_string)
        duration = get_video_duration(mp4videoURL)
        intervals = get_intervals65sec(duration, path_data)
        print(intervals)

        i = int(input("Rentrez l'intervalle souhaité entre 1 et 6 : "))

        start_time1 = intervals[i-1][0]
        end_time1 = intervals[i-1][1]

    else :
        start_time1 = int(input("Donnée le temps en seconde du début de video : "))
        end_time1 = start_time1 + 65

    print(start_time1, end_time1)

    choice_subtitle = int(input("Voulez vous des sous titres dans votre video (1 pour oui, 0 pour non) : "))

    if choice_subtitle == 0 :
        sbtl = False
    elif choice_subtitle == 1 :
        sbtl = True

    def add_subtitles_to_video(video_path: str, text_color, highlight_text_color, highlight_bg_color):
        """Ajoute des sous-titres à une vidéo"""
        try:
            start_time_str = str(start_time1)
            end_time_str = str(end_time1)

            audiofilename = video_path.replace(".mp4", '_trimmed.mp3')

            # Trim the audio using ffmpeg
            ffmpeg.input(video_path).audio.filter('atrim', start=start_time_str, end=end_time_str).output(audiofilename).run(overwrite_output=True)

            # Transcription of video in an SRT file via Whisper Model
            model = WhisperModel('medium', device="cpu", compute_type="int8")
            segments, info = model.transcribe(audiofilename, word_timestamps=True, beam_size=5)
            print("Detected language '%s' with probability %f, duration : %f" % (info.language, info.language_probability, info.duration))
            segments = list(segments)

            wordlevel_info = []

            for segment in segments:
                for word in segment.words:
                    wordlevel_info.append({'word': word.word, 'start': word.start, 'end': word.end})

            with open('data.json', 'w') as f:
                json.dump(wordlevel_info, f, indent=4)

            def split_text_into_lines(data):

                MaxChars = 20
                # maxduration in seconds
                MaxDuration = 2
                # Split if nothing is spoken (gap) for these many seconds
                MaxGap = 1

                subtitles = []
                line = []
                line_duration = 0
                line_chars = 0

                for idx, word_data in enumerate(data):
                    word = word_data["word"]
                    start = word_data["start"]
                    end = word_data["end"]
                    line.append(word_data)
                    line_duration += end - start
                    temp = " ".join(item["word"] for item in line)

                    # Check if adding a new word exceeds the maximum character count or duration
                    new_line_chars = len(temp)
                    duration_exceeded = line_duration > MaxDuration
                    chars_exceeded = new_line_chars > MaxChars
                    if idx > 0:
                        gap = word_data['start'] - data[idx - 1]['end']
                        maxgap_exceeded = gap > MaxGap
                    else:
                        maxgap_exceeded = False

                    if duration_exceeded or chars_exceeded or maxgap_exceeded:
                        if line:
                            subtitle_line = {
                                "word": " ".join(item["word"] for item in line),
                                "start": line[0]["start"],
                                "end": line[-1]["end"],
                                "textcontents": line
                            }
                            subtitles.append(subtitle_line)
                            line = []
                            line_duration = 0
                            line_chars = 0
                if line:
                    subtitle_line = {
                        "word": " ".join(item["word"] for item in line),
                        "start": line[0]["start"],
                        "end": line[-1]["end"],
                        "textcontents": line
                    }
                    subtitles.append(subtitle_line)
                return subtitles

            linelevel_subtitles = split_text_into_lines(wordlevel_info)

            for line in linelevel_subtitles:
                json_str = json.dumps(line, indent=4)

            def create_caption(textJSON, framesize, font="LilitaOne-Regular.ttf", color=text_color, highlight_color=highlight_text_color, bgcolor=highlight_bg_color):
                wordcount = len(textJSON['textcontents'])
                full_duration = textJSON['end'] - textJSON['start']

                word_clips = []
                xy_textclips_positions = []

                x_pos = 0
                y_pos = 0
                line_width = 0  # Total width of words in the current line
                frame_width = framesize[0]
                frame_height = framesize[1]
                x_buffer = frame_width * 1 / 10
                max_line_width = frame_width - 2 * (x_buffer)
                fontsize = int(frame_height * 0.13)

                space_width = ""
                space_height = ""

                for index, wordJSON in enumerate(textJSON['textcontents']):
                    duration = wordJSON['end'] - wordJSON['start']
                    word_clip = TextClip(wordJSON['word'], font=font, fontsize=fontsize, color=color).set_start(
                        textJSON['start']).set_duration(full_duration)
                    word_clip_space = TextClip(" ", font=font, fontsize=fontsize, color=color).set_start(
                        textJSON['start']).set_duration(full_duration)
                    word_width, word_height = word_clip.size
                    space_width, space_height = word_clip_space.size
                    if line_width + word_width + space_width <= max_line_width:
                        # Store info of each word_clip created
                        xy_textclips_positions.append({
                            "x_pos": x_pos,
                            "y_pos": y_pos,
                            "width": word_width,
                            "height": word_height,
                            "word": wordJSON['word'],
                            "start": wordJSON['start'],
                            "end": wordJSON['end'],
                            "duration": duration
                        })

                        word_clip = word_clip.set_position((x_pos, y_pos))
                        word_clip_space = word_clip_space.set_position((x_pos + word_width, y_pos))
                        x_pos = x_pos + word_width + space_width
                        line_width = line_width + word_width + space_width
                    else:
                        # Move to the next line
                        x_pos = 0
                        y_pos = y_pos + word_height + 10
                        line_width = word_width + space_width

                        # Store info of each word_clip created
                        xy_textclips_positions.append({
                            "x_pos": x_pos,
                            "y_pos": y_pos,
                            "width": word_width,
                            "height": word_height,
                            "word": wordJSON['word'],
                            "start": wordJSON['start'],
                            "end": wordJSON['end'],
                            "duration": duration
                        })

                        word_clip = word_clip.set_position((x_pos, y_pos))
                        word_clip_space = word_clip_space.set_position((x_pos + word_width, y_pos))
                        x_pos = word_width + space_width

                    word_clips.append(word_clip)
                    word_clips.append(word_clip_space)

                for highlight_word in xy_textclips_positions:
                    word_clip_highlight = TextClip(highlight_word['word'], font=font, fontsize=fontsize+5,color=highlight_color, bg_color=bgcolor).set_start(highlight_word['start']).set_duration(highlight_word['duration'])
                    word_clip_highlight = word_clip_highlight.set_position((highlight_word['x_pos'], highlight_word['y_pos']))
                    word_clips.append(word_clip_highlight)

                return word_clips, xy_textclips_positions

            input_video = VideoFileClip(video_path)
            frame_size = input_video.size

            all_linelevel_splits = []

            for line in linelevel_subtitles:
                out_clips, positions = create_caption(line, frame_size)

                max_width = 0
                max_height = 0

                for position in positions:
                    x_pos, y_pos = position['x_pos'], position['y_pos']
                    width, height = position['width'], position['height']

                    max_width = max(max_width, x_pos + width)
                    max_height = max(max_height, y_pos + height)

                color_clip = ColorClip(size=(int(max_width * 1.1), int(max_height * 1.1)), color=(64, 64, 64))
                color_clip = color_clip.set_opacity(0)
                color_clip = color_clip.set_start(line['start']).set_duration(line['end'] - line['start'])

                # centered_clips = [each.set_position('center') for each in out_clips]

                clip_to_overlay = CompositeVideoClip([color_clip] + out_clips)
                clip_to_overlay = clip_to_overlay.set_position(("center", 1400))

                all_linelevel_splits.append(clip_to_overlay)

            # Remove the temporary trimmed audio file
            os.remove(audiofilename)
            return all_linelevel_splits

        except Exception as e:
            raise e


    # Télécharger la vidéo YouTube
    download_youtube_video(mp4videoURL)

    # Charger la vidéo d'arrière-plan
    background_video = VideoFileClip(background_path)
    maxduration = background_video.duration

    duration_asked = end_time1 - start_time1

    if duration_asked > maxduration:
        raise ValueError("La durée demandée dépasse la durée totale de la vidéo background.")

    # Generate a random value for duration_asked_start
    duration_asked_start = random.uniform(0, maxduration - duration_asked)

    # Calculate duration_asked_end
    duration_asked_end = duration_asked_start + duration_asked

    # Check if duration_asked_end exceeds the total duration
    if duration_asked_end > maxduration:
        # Adjust duration_asked_end if it exceeds the total duration
        duration_asked_end = maxduration
        duration_asked_start = duration_asked_start - 65

    # Check if the difference between duration_asked_end and duration_asked_start is equal to duration_asked
    if duration_asked_end - duration_asked_start != duration_asked:
        raise ValueError("Invalid random subclip range")

    # Extract the random subclip from the background video
    background_video = background_video.subclip(duration_asked_start, duration_asked_end)
    (w, h) = background_video.size

    # Vérifier si la vidéo d'arrière-plan est au format portrait ou paysage
    is_portrait = h > w

    if is_portrait:
        print("La vidéo d'arrière-plan est au format portrait.")
    else:
        print("La vidéo d'arrière-plan est au format paysage.")
        background_video = background_video.resize(height=1920)
        background_video = background_video.crop(x1=1166.6, y1=0, x2=2246.6, y2=1920)


    # Redimensionner la vidéo téléchargée pour correspondre à la largeur de l'arrière-plan
    overlay_video = VideoFileClip("ytb_path.mp4").subclip(start_time1, end_time1)
    overlay_video = overlay_video.resize(width=background_video.w + 160)

    # Récupérer les dimensions de l'arrière-plan et de la superposition
    background_width, background_height = background_video.size
    overlay_width, overlay_height = overlay_video.size

    # Calculer les coordonnées pour centrer la superposition en haut de l'arrière-plan
    overlay_x = (background_width - overlay_width) // 2

    y_position = 100
    while y_position != 1 and y_position != 2 and y_position != 3 :
        y_position = int(input("Choisissez le positionnement de la video : (1 - Haut, 2 - Milieu, 3 - Bas) : "))

    if y_position == 1 :
        overlay_y = 0

    elif y_position == 2 :
        overlay_y = (background_height - overlay_height) // 2

    else :
        overlay_y = background_height

    if sbtl is True:
        text_color = str(input("Couleur du texte de base en HEXA ou couleur de base : "))
        text_higlight_color = str(input("Couleur du texte highlight en HEXA ou couleur de base : "))
        bg_color = str(input("Couleur du background de l'highlight en HEXA ou couleur de base : "))
        all_linelevel_splits = add_subtitles_to_video("ytb_path.mp4", text_color, text_higlight_color, bg_color)

        # Superposer la vidéo de superposition sur l'arrière-plan
        video_with_overlay = CompositeVideoClip([background_video, overlay_video.set_position((overlay_x, overlay_y))] + all_linelevel_splits, use_bgclip=True)

    else :
        video_with_overlay = CompositeVideoClip([background_video, overlay_video.set_position((overlay_x, overlay_y))], use_bgclip=True)

    # Sauvegarder la vidéo résultante
    video_with_overlay.write_videofile(output_path, fps=24, codec='h264_nvenc', audio_codec='aac', threads=100)

    # Fermer les clips vidéo
    background_video.close()
    overlay_video.close()

def extract_satisfying():
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
            destination_folder = os.path.dirname(os.path.abspath(__file__))

            # Créer le répertoire de destination s'il n'existe pas
            os.makedirs(destination_folder, exist_ok=True)

            # Nom de fichier local souhaité
            local_filename = "satisfaisant.mp4"

            # Télécharger la vidéo dans le répertoire de destination avec le nom souhaité
            destination_path = os.path.join(destination_folder, local_filename)
            random_video.GetContentFile(destination_path)
            print(f"Vidéo téléchargée avec succès sous le nom '{local_filename}'.")
            return (local_filename, drive)
        else:
            print("Aucune vidéo trouvée dans le dossier spécifié.")
    else:
        print("Dossier spécifié non trouvé ou multiple dossiers trouvés.")



if __name__ == "__main__":
    #Recupère la video background dans le drive
    satisfying_flname, drive = extract_satisfying()

    # Entrer le lien de la vidéo YouTube
    video_url = input("Entrez le lien de la vidéo YouTube : ")

    # Chemins d'accès aux vidéos
    background_video_path = satisfying_flname

    # Chemin de sortie pour la vidéo résultante
    output_path = "output.mp4"
    overlay_videos(background_video_path, output_path, video_url)


    # Chemin dans Google Drive où enregistrer la vidéo
    drive_folder_id = '1JUVVFnhPp0Bl7uCrAFlzwE_2z0Z8t3xj'

    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    part_filename = f'part_{random_string}".mp4"'
    part_path = "output.mp4"

    # Création d'un fichier dans Google Drive
    file_drive = drive.CreateFile({'title': part_filename, 'parents': [{'id': drive_folder_id}]})

    # Attachez le contenu du fichier local au fichier Google Drive
    file_drive.SetContentFile(part_path)

    # Téléversement du fichier vers Google Drive
    file_drive.Upload()
