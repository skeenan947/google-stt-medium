import ffmpeg
from google.cloud import storage
from utils import transcribe, subtitle_generation

bucket_name = "my-bucket"
project = "my-project"

video = "some_file.mp4"
# trim .mp4 off of the filename
video_name = video.split('.')[0]
# rip audio from video
stream = ffmpeg.input(video)
mp3 = "{}.mp3".format(video_name)
audio = ffmpeg.output(stream, mp3)
#ffmpeg.run(audio)

# Set up the storage client
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)

# upload audio to cloud storage
blob = bucket.blob(mp3)
blob.upload_from_filename(mp3)
print("Uploaded {} to Cloud Storage.".format(mp3))

# The output path of the transcription result.
workspace = "gs://{}/transcripts".format(bucket_name)

# The name of the audio file to transcribe:
gcs_uri = "gs://{}/{}".format(bucket_name, mp3, model="chirp")

# Recognizer resource name:
recognizer = "projects/{}/locations/us-central1/recognizers/_".format(project)

print("Transcribing {}...".format(gcs_uri))
# Call our transcribe function (see below for source)
batch_recognize_results = transcribe(workspace, gcs_uri, recognizer)

subFile = "{}.srt".format(video_name)
print("Generating SRT file for {}...".format(video))
subs = subtitle_generation(batch_recognize_results, subFile)

storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)
blob = bucket.blob("{}.srt".format(video))

blob.upload_from_filename(subFile)
print("Uploaded {} to Cloud Storage.".format(subFile))