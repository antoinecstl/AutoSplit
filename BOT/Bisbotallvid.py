import nextcord
from nextcord.ext import commands
from apikeys import botoken
import ds_video as ds
import asyncio
import re

client = commands.Bot(command_prefix= '!', intents= nextcord.Intents.all())
is_running = False
going = False
request_queue = asyncio.Queue()

@client.event
async def on_ready():
    await client.change_presence(status=nextcord.Status.idle, activity=nextcord.Activity(type = nextcord.ActivityType.listening, name = ("your !go")))
    print("Bis bot is now ready for use !")
    print("------------------------------")

async def process_queue():
    global is_running, going
    while True:
        if not request_queue.empty() and not is_running:
            ctx = await request_queue.get()
            is_running = True
            await process_go_command(ctx)
            is_running = False
        await asyncio.sleep(1)  # Sleep for a short duration to avoid busy loop

@client.command()
async def stop(ctx):
    global going
    if going :
        going = False
        embed = nextcord.Embed(title="Command stopped")
        await ctx.send(embed=embed)
    else :
        await ctx.send("Bot isn't running")
@client.command()
async def process_go_command(ctx):
    # Démarrez le traitement vidéo
    await process_video(ctx)


async def process_video(ctx):
    try:
        global is_running, going, pos_sbtl, text_highlight_color
        is_running = True
        going = True

        def check(m):
            return m.author.id == ctx.author.id

        # Vérifier si l'utilisateur a déjà un canal personnalisé
        existing_channels = [c for c in ctx.guild.text_channels if ctx.author in c.members]

        if existing_channels:
            # Trouver le dernier canal personnalisé de l'utilisateur
            last_channel = existing_channels[-1]
            match = re.search(r'-(\d+)$', last_channel.name)

            if match:
                last_channel_number = int(match.group(1))
                new_channel_number = last_channel_number + 1
            else:
                # Si aucun numéro n'est trouvé, commencez à 1
                new_channel_number = 1

            new_channel_name = f"Generation-{ctx.author.display_name}-{new_channel_number}"
        else:
            new_channel_name = f"Generation-{ctx.author.display_name}"

        # Trouver la catégorie parente
        category = nextcord.utils.get(ctx.guild.categories, name='Generator')

        # Créer un nouveau canal personnalisé dans la catégorie spécifiée
        overwrites = {
            ctx.guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
            ctx.author: nextcord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True),
            ctx.guild.me: nextcord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True)
        }

        channel = await ctx.guild.create_text_channel(name=new_channel_name, overwrites=overwrites, category=category)

        embed = nextcord.Embed(title=f"Bisbot is now running for you !")
        await channel.send(embed=embed)
        await channel.send(f"{ctx.author.mention}")

        await channel.send("**Enter the youtube video link : **")

        if going:
            ytb_url = await get_youtube_url(channel, check)
        else:
            return

        if going:
            heatmap_value = await get_heatmap_choice(channel, check)
            if heatmap_value == 1:
                if going:
                    path_data, duration, intervals = await get_heatmap_svg(channel, check, ytb_url)
                    start_time1, end_time1 = await choose_intervals(channel, check, intervals)
                else:
                    return

            else:
                if going:
                    start_time1, end_time1 = await get_video_time(channel, check, ytb_url)
                else:
                    return
        else:
            return

        if going:
            y_position = await choose_position(channel, check)
        else:
            return

        if going:
            sbtl = await choose_sbtl(channel, check)
        else:
            return

        if going:
            if sbtl == 1:
                pos_sbtl = await choose_sbtl_position(channel, check)
                text_color, bg_color = await sbtl_personalisation_scroll(channel, check)
        else:
            return


        await channel.send("Downloading background video....")
        ds.extract_satisfying()
        await channel.send("Background video downloaded")
        # Recupère la video background dans le drive
        satisfying_flname = "satisfaisant.mp4"

        # Chemins d'accès aux vidéos
        background_path = satisfying_flname

        background_video = ds.VideoFileClip(background_path)
        maxduration = background_video.duration

        # Télécharger la vidéo YouTube
        await channel.send("Downloading youtube video")
        ds.download_youtube_video(ytb_url)
        await channel.send("Youtube video Downloaded")

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
        overlay_video = overlay_video.resize(width=background_video.w + 400)

        # Récupérer les dimensions de l'arrière-plan et de la superposition
        background_width, background_height = background_video.size
        overlay_width, overlay_height = overlay_video.size

        # Calculer les coordonnées pour centrer la superposition en haut de l'arrière-plan
        overlay_x = (background_width - overlay_width) // 2

        if y_position == 1:
            overlay_y = 0

        elif y_position == 2:
            overlay_y = (background_height - overlay_height) // 2

        else :
            overlay_y = background_height - overlay_height

        print(f"sbtl : {sbtl}")

        if sbtl == 1:
            await channel.send("Generating Subtitles... (Can take up to 1 minutes)")
            all_linelevel_splits = add_subtitles_to_video(pos_sbtl, start_time1, end_time1, "ytb_path.mp4", text_color, text_highlight_color, bg_color)
            video_with_overlay = ds.CompositeVideoClip([background_video, overlay_video.set_position((overlay_x, overlay_y))] + all_linelevel_splits, use_bgclip=True)
        else :
            video_with_overlay = ds.CompositeVideoClip([background_video, overlay_video.set_position((overlay_x, overlay_y))], use_bgclip=True)

        # Chemin de sortie pour la vidéo résultante
        output_path = "output.mp4"

        # Sauvegarder la vidéo résultante
        await channel.send("Processing.... (Can take up to 4 minutes)")
        video_with_overlay.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
        background_video.close()
        overlay_video.close()
        drive_folder_id = ds.drive_upload()

        drive_folder_url = f"https://drive.google.com/drive/u/1/folders/{drive_folder_id}"
        message = f"Your video is finished !\n\n Here is the directory adress : {drive_folder_url}"
        embed = nextcord.Embed(title=message)
        await channel.send(embed=embed)

        is_running = False
        going = False

    except Exception as e:
        await ctx.send(f"Video processing failed for user {ctx.author.mention}: {str(e)}")
    finally:
        is_running = False
        going = False

async def get_youtube_url(ctx, check):
    global going
    try:
        ytb_url = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
        ytb_url = ytb_url.content

        while ytb_url == "!go" or ytb_url == "!position":
            await ctx.send("Enter the youtube video link : ")
            ytb_url = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
            ytb_url = ytb_url.content

        return ytb_url

    except asyncio.TimeoutError:
        await ctx.send("No response received within 30 seconds. Command stopped")
        going = False
        return

async def get_heatmap_choice(ctx, check):
    global going
    await ctx.send("Do you have any heatmap **(yes or no)** : ")
    try:
        heatmap_choice = await asyncio.wait_for(client.wait_for('message', check=check), timeout=20)
        heatmap_choice = heatmap_choice.content
        if heatmap_choice.lower() == "yes" :
            return 1
        elif heatmap_choice.lower() == "no" :
            return 0
        else:
            await ctx.send("Invalid choice. Please enter 'yes' or 'no'.")
            return await get_heatmap_choice(ctx, check)

    except asyncio.TimeoutError:
        await ctx.send("No response received within 20 seconds. Command stopped")
        going = False
        return

async def get_heatmap_svg(ctx, check, ytb_url):
    global going
    if going :
        await ctx.send("Enter heatmap's SVG : ")
        try:
            user_message = await asyncio.wait_for(client.wait_for('message', check=check), timeout=90)

        except asyncio.TimeoutError:
            await ctx.send("No response received within 90 seconds. Command stopped")
            going = False
            return

        if user_message.attachments:
            attachment = user_message.attachments[0]
            if attachment.filename.endswith('.txt'):
                # Télécharge le fichier
                await attachment.save("svg.txt")
            else:
                await ctx.send("Le fichier attaché doit être un fichier .txt.")
        else:
            await ctx.send("Aucun fichier attaché trouvé.")
            await get_heatmap_svg(ctx, check, ytb_url)

        file = open(r"svg.txt", "rt")
        heatmap = file.read()
        file.close()

        path_data = ds.parse_coordinates(heatmap)
        duration = ds.get_video_duration(ytb_url)
        intervals = ds.get_intervals65sec(duration, path_data)

        return (path_data, duration, intervals)

    else:
        return

async def get_video_time(ctx, check, ytb_url):
    global going

    await ctx.send("Enter the start time (in seconds) of the video : ")
    start_time1 = None

    while start_time1 is None:
        try:
            user_input = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
            start_time1 = int(user_input.content)
        except ValueError:
            await ctx.send("Please enter a valid number.")
        except asyncio.TimeoutError:
            await ctx.send("No response received within 30 seconds. Command stopped")
            going = False
            return

    end_time1 = int(start_time1) + 65
    print(start_time1, end_time1)
    await ctx.send(f"Here is your video timecode [Start : {start_time1}, End : {end_time1}]")
    return start_time1, end_time1

async def choose_intervals (ctx, check, intervals):
    global going

    await ctx.send(f"The intervals classed by the highest to the lowest : {intervals}")
    i = 9999

    while i < 1 or i > 6:
        if going:
            await ctx.send("Choose the interval between 1 to 6 :")
            try:
                i = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
                i = int(i.content)

            except asyncio.TimeoutError:
                await ctx.send("No response received within 30 seconds. Command stopped")
                going = False
                return
        else:
            return
    start_time1 = intervals[i - 1][0]
    end_time1 = intervals[i - 1][1]

    return start_time1, end_time1

async def choose_sbtl (ctx, check):
    global going

    # Subtitle
    sbtl = 12

    while sbtl != 0 and sbtl != 1:
        if going:
            await ctx.send("Add subtitles to your video **(yes or no)** [Editing time will be about 2 minutes longer] :")
            try:
                subtitleprechoice = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
                subtitleprechoice = subtitleprechoice.content

            except asyncio.TimeoutError:
                await ctx.send("No response received within 30 seconds. Command stopped")
                going = False
                return

            if subtitleprechoice.lower() == "yes":
                sbtl = 1

            elif subtitleprechoice.lower() == "no":
                sbtl = 0

            return sbtl

        else:
            return

async def choose_position (ctx, check):
    global going

    y_position = 100
    while y_position != 1 and y_position != 2 and y_position != 3:

        if going:
            await ctx.send("Choose the video position | **1 - High** | **2 - Middle** | **3 - Low** | : ")
            try:
                y_position = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
                y_position = y_position.content

            except asyncio.TimeoutError:
                await ctx.send("No response received within 30 seconds. Command stopped")
                going = False
                return

            y_position = int(y_position)
            return y_position
        else:
            return

async def choose_sbtl_position(ctx, check):
    global going

    sbtl_pos = 20303
    while sbtl_pos != 1 and sbtl_pos != 2:
        if going:
            await ctx.send("Choose the subtitle position | **1 - Middle** | **2 - Low** |")
            try:
                sbtl_pos = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
                sbtl_pos = sbtl_pos.content

            except asyncio.TimeoutError:
                await ctx.send("No response received within 30 seconds. Command stopped")
                going = False
                return

            sbtl_pos = int(sbtl_pos)

        else:
            return

    return sbtl_pos

def add_subtitles_to_video(pos_sbtl, start_time1, end_time1, video_path: str, text_color, highlight_text_color, highlight_bg_color = None):
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

        def create_caption(textJSON, framesize, font="salma.otf", color=text_color, highlight_color=highlight_text_color, bgcolor=highlight_bg_color):
            wordcount = len(textJSON['textcontents'])
            full_duration = textJSON['end'] - textJSON['start']

            word_clips = []
            xy_textclips_positions = []

            if pos_sbtl == 1:
                y_pos = framesize[1] * 0.32

            else:
                y_pos = framesize[1] * 0.6


            x_pos = 5
            # max_height = 0
            frame_width = framesize[0]
            frame_height = framesize[1]
            x_buffer = frame_width * 2 / 12
            y_buffer = frame_height * 0.9
            fontsize = int(frame_height * 0.128)

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
                if x_pos + word_width + space_width > frame_width - 2 * x_buffer:
                    # Move to the next line
                    x_pos = 5
                    y_pos = y_pos + word_height + 35

                    # Store info of each word_clip created
                    xy_textclips_positions.append({
                        "x_pos": x_pos + x_buffer/2,
                        "y_pos": y_pos + y_buffer,
                        "width": word_width,
                        "height": word_height,
                        "word": wordJSON['word'],
                        "start": wordJSON['start'],
                        "end": wordJSON['end'],
                        "duration": duration
                    })

                    word_clip = word_clip.set_position((x_pos + (x_buffer/2), y_pos + y_buffer))
                    word_clip_space = word_clip_space.set_position((x_pos + word_width + x_buffer, y_pos + y_buffer))
                    x_pos = word_width + space_width
                else:
                    # Store info of each word_clip created
                    xy_textclips_positions.append({
                        "x_pos": x_pos + x_buffer/2,
                        "y_pos": y_pos + y_buffer,
                        "width": word_width,
                        "height": word_height,
                        "word": wordJSON['word'],
                        "start": wordJSON['start'],
                        "end": wordJSON['end'],
                        "duration": duration
                    })

                    word_clip = word_clip.set_position((x_pos + x_buffer/2, y_pos + y_buffer))
                    word_clip_space = word_clip_space.set_position((x_pos + word_width + x_buffer, y_pos + y_buffer))
                    x_pos = x_pos + word_width + space_width

                word_clips.append(word_clip)
                word_clips.append(word_clip_space)

            for highlight_word in xy_textclips_positions:
                word_clip_highlight = ds.TextClip(highlight_word['word'], font=font, fontsize=fontsize, color=highlight_color, bg_color=bgcolor).set_start(highlight_word['start']).set_duration(highlight_word['duration'])
                word_clip_highlight = word_clip_highlight.set_position((highlight_word['x_pos'], highlight_word['y_pos']))
                word_clips.append(word_clip_highlight)

            return word_clips, xy_textclips_positions

        input_video = ds.VideoFileClip(video_path)
        frame_size = input_video.size

        all_linelevel_splits = []

        for line in linelevel_subtitles:
            out, positions = create_caption(line, frame_size)
            all_linelevel_splits.extend(out)

        # Remove the temporary trimmed audio file
        ds.os.remove(audiofilename)
        return all_linelevel_splits

    except Exception as e:
        raise e

async def sbtl_personalisation_scroll (ctx, check):
    global going
    if going:
        await ctx.send("Basic subtitle color (Hexa or colorname) : ")
        try:
            text_color = await asyncio.wait_for(client.wait_for('message', check=check), timeout=90)
            text_color = text_color.content

        except asyncio.TimeoutError:
            await ctx.send("No response received within 90 seconds. Command stopped")
            going = False
            return
    else:
        return

    if going:
        await ctx.send("Highlight subtitle color (Hexa or colorname) : ")
        try:
            text_highlight_color = await asyncio.wait_for(client.wait_for('message', check=check), timeout=90)
            text_highlight_color = text_highlight_color.content

        except asyncio.TimeoutError:
            await ctx.send("No response received within 90 seconds. Command stopped")
            going = False
            return
    else:
        return

    # Subtitle
    bck = 12
    while bck != 0 and bck != 1:
        if going:
            await ctx.send("Add a background color to your subtitles **(yes or no)** :")
            try:
                bck_ask = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
                bck_ask = bck_ask.content

            except asyncio.TimeoutError:
                await ctx.send("No response received within 30 seconds. Command stopped")
                going = False
                return

        else:
            return

        if bck_ask == "yes" or bck_ask == "Yes":
            bck = 1
        elif bck_ask == "no" or bck_ask == "No":
            bck = 0
    if bck == 1:
        if going:
            await ctx.send("Highlight background color (hexa or colorname) : ")
            try:
                bg_color = await asyncio.wait_for(client.wait_for('message', check=check), timeout=90)
                bg_color = bg_color.content

            except asyncio.TimeoutError:
                await ctx.send("No response received within 90 seconds. Command stopped")
                going = False
                return
        else:
            return
    else:
        bg_color = "None"

    return text_color, bg_color, text_highlight_color

async def sbtl_personalisation_word(ctx, check):
    global going

    if going:
        await ctx.send("Basic subtitle color (Hexa or colorname) : ")
        try:
            text_color = await asyncio.wait_for(client.wait_for('message', check=check), timeout=90)
            text_color = text_color.content

        except asyncio.TimeoutError:
            await ctx.send("No response received within 90 seconds. Command stopped")
            going = False
            return
    else:
        return

    bck = 12
    while bck != 0 and bck != 1:
        if going:
            await ctx.send("Add a background color to your subtitles **(yes or no)** :")
            try:
                bck_ask = await asyncio.wait_for(client.wait_for('message', check=check), timeout=30)
                bck_ask = bck_ask.content

            except asyncio.TimeoutError:
                await ctx.send("No response received within 30 seconds. Command stopped")
                going = False
                return

        else:
            return

        if bck_ask == "yes" or bck_ask == "Yes":
            bck = 1
        elif bck_ask == "no" or bck_ask == "No":
            bck = 0
    if bck == 1:
        if going:
            await ctx.send("Highlight background color (hexa or colorname) : ")
            try:
                bg_color = await asyncio.wait_for(client.wait_for('message', check=check), timeout=90)
                bg_color = bg_color.content

            except asyncio.TimeoutError:
                await ctx.send("No response received within 90 seconds. Command stopped")
                going = False
                return
        else:
            return
    else:
        bg_color = "None"
    return text_color, bg_color

def one_word_sub(start_time1, end_time1, video_path: str, text_color, highlight_bg_color = None):
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

        def create_caption(wordlevel_info, framesize, font="LilitaOne-Regular.ttf", color=text_color, bgcolor=highlight_bg_color):
            wordcount = len(wordlevel_info)
            full_duration = wordlevel_info[-1]['end'] - wordlevel_info[0]['start']

            word_clips = []
            frame_height = framesize[1]
            fontsize = int(frame_height * 0.14)

            for wordJSON in wordlevel_info:
                duration = wordJSON['end'] - wordJSON['start']
                word_clip = ds.TextClip(wordJSON['word'], font=font, fontsize=fontsize, color=color,bg_color=highlight_bg_color).set_start(wordJSON['start']).set_duration(duration).set_position(('center', 'center'))
                word_clips.append(word_clip)

            return word_clips

        input_video = ds.VideoFileClip(video_path)
        frame_size = input_video.size
        word_clips = create_caption(wordlevel_info, frame_size)

        # Remove the temporary trimmed audio file
        ds.os.remove(audiofilename)
        return word_clips

    except Exception as e:
        raise e

user_positions = {}

@client.command()
async def go(ctx):
    if ctx.author.id in user_positions and going == True:
        position = user_positions[ctx.author.id]
        if position == 1:
            await ctx.send("The code is already running for you, it's your turn !")
            return
        else:
            await ctx.send(f"The code is already running, you're in the queue. Your position is: {position}")
    else:
        await request_queue.put(ctx)
        position = request_queue.qsize()
        user_positions[ctx.author.id] = position
        await ctx.send(f"You've been added to the queue. Your position is: {position}")

@client.command()
async def position(ctx):
    user = ctx.author
    position = user_positions.get(user.id)
    if position is not None:
        if position == 1:
            await ctx.send(f"You're {position}, the code is running for you, it's your turn !")
        else :
            await ctx.send(f"Your current position in the queue is: {position}")
    else:
        await ctx.send("You are not in the queue.")

client.loop.create_task(process_queue())
client.run(token=botoken())