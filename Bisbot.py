import nextcord
from nextcord.ext import commands
from apikeys import botoken
import ds_video as ds


client = commands.Bot(command_prefix= '!', intents= nextcord.Intents.all())

@client.event
async def on_ready():
    await client.change_presence(status=nextcord.Status.idle, activity=nextcord.Activity(type = nextcord.ActivityType.listening, name = ("your !go")))
    print("Bis bot is now ready for use !")
    print("------------------------------")


@client.command()
async def go(ctx):

    await ctx.send(f"Start of video treatment for {ctx.author.mention}")
    embed = nextcord.Embed(title="Bisbot is running for you !")
    await ctx.message.author.send(embed=embed)
    await ctx.message.author.send("Enter the youtube video link : ")
    def check(m):
        return m.author.id == ctx.author.id

    ytb_url = await client.wait_for('message', check=check)
    ytb_url = ytb_url.content

    heatmap_value = 999999

    while heatmap_value != 0 and heatmap_value != 1 :

        await ctx.message.author.send("Do you have any heatmap (Answer by yes or no) : ")
        heatmap_choice = await client.wait_for('message', check=check)
        heatmap_choice = heatmap_choice.content

        if heatmap_choice == "yes" or heatmap_choice == "Yes" :
            heatmap_value = 1
            print("heatmap")
            await ctx.message.author.send("Enter heatmap's SVG : ")
            user_message = await client.wait_for('message', check=check)
            if user_message.attachments:
                attachment = user_message.attachments[0]
                if attachment.filename.endswith('.txt'):
                    # Télécharge le fichier
                    await attachment.save("svg.txt")
                else:
                    await ctx.message.author.send("Le fichier attaché doit être un fichier .txt.")
            else:
                await ctx.message.author.send("Aucun fichier attaché trouvé.")

            file = open(r"svg.txt","rt")
            heatmap = file.read()
            file.close()

            path_data = ds.parse_coordinates(heatmap)
            duration = ds.get_video_duration(ytb_url)
            intervals = ds.get_intervals65sec(duration, path_data)
            print(intervals)

            await ctx.message.author.send(f"The intervals classed by the highest to the lowest : {intervals}")
            i = 9999
            while i < 1 or i > 6:
                await ctx.message.author.send("Choose the interval between 1 to 6 :")
                i = await client.wait_for('message', check=check)
                i = int(i.content)

            start_time1 = intervals[i - 1][0]
            end_time1 = intervals[i - 1][1]

        elif heatmap_choice == "no" or heatmap_choice == "No":
            heatmap_value = 0
            print("Pas d'heatmap")

            await ctx.message.author.send("Enter the start time (in seconds) of the video : ")
            start_time1 = await client.wait_for('message', check=check)
            start_time1 = start_time1.content
            start_time1 = int(start_time1)
            end_time1 = int(start_time1) + 65
            print(start_time1, end_time1)
            await ctx.message.author.send(f"Here is your video timecode [Start : {start_time1}, End : {end_time1}]")

        else :
            heatmap_value = 1234
            start_time1 = 0
            end_time1 = 0

    await ctx.message.author.send("Downloading background video....")
    ds.extract_satisfying()
    # Recupère la video background dans le drive
    satisfying_flname = "satisfaisant.mp4"

    # Chemins d'accès aux vidéos
    background_path = satisfying_flname

    background_video = ds.VideoFileClip(background_path)
    maxduration = background_video.duration

    # Télécharger la vidéo YouTube
    await ctx.message.author.send("Downloading....")
    ds.download_youtube_video(ytb_url)

    #Subtitle
    sbtl = 12
    while sbtl != 0 and sbtl != 1:
        await ctx.message.author.send("Add subtitles to your video (yes or no) :")
        subtitleprechoice = await client.wait_for('message', check=check)
        subtitleprechoice = subtitleprechoice.content

        if subtitleprechoice == "yes" or subtitleprechoice == "Yes" :
            sbtl = 1
        elif subtitleprechoice == "no" or subtitleprechoice =="No" :
            sbtl = 0
    print(f"sbtl : {sbtl}")
    def add_subtitles_to_video(video_path: str, text_color, highlight_text_color, highlight_bg_color):
        """Ajoute des sous-titres à une vidéo"""
        try:
            start_time_str = str(start_time1)
            end_time_str = str(end_time1)

            audiofilename = video_path.replace(".mp4", '_trimmed.mp3')

            # Trim the audio using ffmpeg
            ds.ffmpeg.input(video_path).audio.filter('atrim', start=start_time_str, end=end_time_str).output(audiofilename).run(overwrite_output=True)

            # Transcription of video in an SRT file via Whisper Model
            model = ds.WhisperModel('medium', device="cpu", compute_type="int8")
            segments, info = model.transcribe(audiofilename, word_timestamps=True, beam_size=5)
            print("Detected language '%s' with probability %f, duration : %f" % (info.language, info.language_probability, info.duration))
            segments = list(segments)

            wordlevel_info = []

            for segment in segments:
                for word in segment.words:
                    wordlevel_info.append({'word': word.word, 'start': word.start, 'end': word.end})

            with open('data.json', 'w') as f:
                ds.json.dump(wordlevel_info, f, indent=4)

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
                json_str = ds.json.dumps(line, indent=4)

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
                    word_clip = ds.TextClip(wordJSON['word'], font=font, fontsize=fontsize, color=color).set_start(
                        textJSON['start']).set_duration(full_duration)
                    word_clip_space = ds.TextClip(" ", font=font, fontsize=fontsize, color=color).set_start(
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
                    word_clip_highlight = ds.TextClip(highlight_word['word'], font=font, fontsize=fontsize+5,color=highlight_color, bg_color=bgcolor).set_start(highlight_word['start']).set_duration(highlight_word['duration'])
                    word_clip_highlight = word_clip_highlight.set_position((highlight_word['x_pos'], highlight_word['y_pos']))
                    word_clips.append(word_clip_highlight)

                return word_clips, xy_textclips_positions

            input_video = ds.VideoFileClip(video_path)
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

                color_clip = ds.ColorClip(size=(int(max_width * 1.1), int(max_height * 1.1)), color=(64, 64, 64))
                color_clip = color_clip.set_opacity(0)
                color_clip = color_clip.set_start(line['start']).set_duration(line['end'] - line['start'])

                # centered_clips = [each.set_position('center') for each in out_clips]

                clip_to_overlay = ds.CompositeVideoClip([color_clip] + out_clips)
                clip_to_overlay = clip_to_overlay.set_position(("center", 1400))

                all_linelevel_splits.append(clip_to_overlay)

            # Remove the temporary trimmed audio file
            ds.os.remove(audiofilename)
            return all_linelevel_splits

        except Exception as e:
            raise e

        # Charger la vidéo d'arrière-plan

    duration_asked = end_time1 - start_time1

    if duration_asked > maxduration:
        raise ValueError("La durée demandée dépasse la durée totale de la vidéo background.")

    # Generate a random value for duration_asked_start
    duration_asked_start = ds.random.uniform(0, maxduration - duration_asked)

    # Calculate duration_asked_end
    duration_asked_end = duration_asked_start + duration_asked

    # Check if duration_asked_end exceeds the total duration
    if duration_asked_end > maxduration:
        # Adjust duration_asked_end if it exceeds the total duration
        duration_asked_end = maxduration
        duration_asked_start = duration_asked_start - 65

    print(duration_asked)
    diff = duration_asked_end - duration_asked_start
    diff = round(diff, 1)

    # Check if the difference between duration_asked_end and duration_asked_start is equal to duration_asked
    if diff != duration_asked:
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
    overlay_video = ds.VideoFileClip("ytb_path.mp4").subclip(start_time1, end_time1)
    overlay_video = overlay_video.resize(width=background_video.w + 160)

    # Récupérer les dimensions de l'arrière-plan et de la superposition
    background_width, background_height = background_video.size
    overlay_width, overlay_height = overlay_video.size

    # Calculer les coordonnées pour centrer la superposition en haut de l'arrière-plan
    overlay_x = (background_width - overlay_width) // 2

    y_position = 100
    while y_position != 1 and y_position != 2 and y_position != 3:
        await ctx.message.author.send("Choose the video position (1 - High, 2 - Middle, 3 - Low) : ")
        y_position = await client.wait_for('message', check=check)
        y_position = y_position.content
        y_position = int(y_position)

    if y_position == 1:
        overlay_y = 0

    elif y_position == 2:
        overlay_y = (background_height - overlay_height) // 2

    else:
        overlay_y = background_height
    print(f"sbtl : {sbtl}")
    if sbtl == 1 :
        await ctx.message.author.send("Basic subtitle color (Hexa or colorname) : ")
        text_color = await client.wait_for('message', check=check)
        text_color = text_color.content
        await ctx.message.author.send("Highlight subtitle color (Hexa or colorname) : ")
        text_highlight_color = await client.wait_for('message', check=check)
        text_highlight_color = text_highlight_color.content
        await ctx.message.author.send("Highlight background color (hexa or colorname) : ")
        bg_color = await client.wait_for('message', check=check)
        bg_color = bg_color.content

        all_linelevel_splits = add_subtitles_to_video("ytb_path.mp4", text_color, text_highlight_color, bg_color)
        # Superposer la vidéo de superposition sur l'arrière-plan
        video_with_overlay = ds.CompositeVideoClip([background_video, overlay_video.set_position((overlay_x, overlay_y))] + all_linelevel_splits,use_bgclip=True)

    else :
        video_with_overlay = ds.CompositeVideoClip([background_video, overlay_video.set_position((overlay_x, overlay_y))], use_bgclip=True)

    # Chemin de sortie pour la vidéo résultante
    output_path = "output.mp4"

    # Sauvegarder la vidéo résultante
    await ctx.message.author.send("Processing....")
    video_with_overlay.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', threads=100)

    # Fermer les clips vidéo
    background_video.close()
    overlay_video.close()

    drive_folder_id = ds.drive_upload()

    drive_folder_url = f"https://drive.google.com/drive/u/1/folders/{drive_folder_id}"
    message = f"Your video is finished !\n\n Here is the directory adress : {drive_folder_url}"
    embed = nextcord.Embed(title=message)
    await ctx.message.author.send(embed=embed)

client.run(token=botoken())