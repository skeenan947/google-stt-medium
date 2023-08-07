from google.cloud import storage
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
import re
import srt
import datetime

def transcribe(workspace, gcs_uri, recognizer, model="chirp"):
    client = SpeechClient(
        client_options=ClientOptions(
            api_endpoint="us-central1-speech.googleapis.com",
        )
    )

    config = cloud_speech.RecognitionConfig(
    auto_decoding_config={},
    language_codes=["en-US"],
    model=model,
    features=cloud_speech.RecognitionFeatures(
    enable_word_time_offsets=True,
    ),
    )

    output_config = cloud_speech.RecognitionOutputConfig(
    gcs_output_config=cloud_speech.GcsOutputConfig(
        uri=workspace),
    )

    files = [cloud_speech.BatchRecognizeFileMetadata(
        uri=gcs_uri
    )]

    request = cloud_speech.BatchRecognizeRequest(
        recognizer=recognizer, config=config, files=files, recognition_output_config=output_config
    )
    operation = client.batch_recognize(request=request,timeout=1200)
    result = operation.result(timeout=1200)

    file_results = result.results[gcs_uri]

    output_bucket, output_object = re.match(
        r"gs://([^/]+)/(.*)", file_results.uri
    ).group(1, 2)

    storage_client = storage.Client()
    bucket = storage_client.bucket(output_bucket)
    blob = bucket.blob(output_object)
    results_bytes = blob.download_as_bytes()
    batch_recognize_results = cloud_speech.BatchRecognizeResults.from_json(
        results_bytes, ignore_unknown_fields=True
    )
    return batch_recognize_results


def subtitle_generation(speech_to_text_response, outfile, bin_size=3):
    """We define a bin of time period to display the words in sync with audio. 
    Here, bin_size = 3 means each bin is of 3 secs. 
    All the words in the interval of 3 secs in result will be grouped togather."""
    transcriptions = []
    index = 0
    
    # Credit to: https://github.com/darshan-majithiya/Generate-SRT-File-using-Google-Cloud-s-Speech-to-Text-API/
    for result in speech_to_text_response.results:
        try:
            if result.alternatives[0].words[0].start_offset.seconds:
                # bin start -> for first word of result
                start_sec = result.alternatives[0].words[0].start_offset.seconds 
                start_microsec = result.alternatives[0].words[0].start_offset.microseconds
            else:
                # bin start -> For First word of response
                start_sec = 0
                start_microsec = 0 
            end_sec = start_sec + bin_size # bin end sec
            
            # for last word of result
            last_word_end_sec = result.alternatives[0].words[-1].end_offset.seconds
            last_word_end_microsec = result.alternatives[0].words[-1].end_offset.microseconds
            
            # bin transcript
            transcript = result.alternatives[0].words[0].word
            
            index += 1 # subtitle index
            
            for i in range(len(result.alternatives[0].words) - 1):
                try:
                    word = result.alternatives[0].words[i + 1].word
                    word_start_sec = result.alternatives[0].words[i + 1].start_offset.seconds
                    word_start_microsec = result.alternatives[0].words[i + 1].start_offset.microseconds
                    word_end_sec = result.alternatives[0].words[i + 1].end_offset.seconds
                    word_end_microsec = result.alternatives[0].words[i + 1].end_offset.microseconds
                    
                    if word_end_sec < end_sec:
                        transcript = transcript + " " + word
                    else:
                        previous_word_end_sec = result.alternatives[0].words[i].end_offset.seconds
                        previous_word_end_microsec = result.alternatives[0].words[i].end_offset.microseconds
                        
                        # append bin transcript
                        transcriptions.append(srt.Subtitle(index, datetime.timedelta(0, start_sec, start_microsec), datetime.timedelta(0, previous_word_end_sec, previous_word_end_microsec), transcript))
                        
                        # reset bin parameters
                        start_sec = word_start_sec
                        start_microsec = word_start_microsec
                        end_sec = start_sec + bin_size
                        transcript = result.alternatives[0].words[i + 1].word
                        
                        index += 1
                except IndexError:
                    pass
            # append transcript of last transcript in bin
            transcriptions.append(srt.Subtitle(index, datetime.timedelta(0, start_sec, start_microsec), datetime.timedelta(0, last_word_end_sec, last_word_end_microsec), srt.make_legal_content(transcript)))
            index += 1
        except IndexError:
            pass
    
    # turn transcription list into subtitles
    #print(transcriptions)
    #subtitles = srt.compose(transcriptions)
    #return subtitles
    subFile = open(outfile, "w")
    subArr = []
    for sub in transcriptions:
        subArr.append(sub.to_srt())

    subFile.writelines(subArr)
    subFile.close()
    return transcriptions
