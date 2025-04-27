import json
import boto3
import uuid

polly = boto3.client('polly')
s3 = boto3.client('s3')

S3_BUCKET_NAME = 'ai-sales-voice-bucket'

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        if 'body' in event:
            body_content = event['body']
            if isinstance(body_content, str) and body_content.strip():
                event = json.loads(body_content)
            elif isinstance(body_content, dict):
                event = body_content

        if isinstance(event, str) and event.strip():
            event = json.loads(event)

        text = event['reply']

        polly_response = polly.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Zhiyu'
        )

        # 存到 requestaudio/
        audio_key = f'requestaudio/{str(uuid.uuid4())}.mp3'

        print(f"Uploading MP3 to S3 at {audio_key}")

        s3.upload_fileobj(
            polly_response['AudioStream'],
            S3_BUCKET_NAME,
            audio_key,
            ExtraArgs={'ContentType': 'audio/mpeg'}
        )

        # 回傳：包含原始資料 + audio_key
        return {
            'statusCode': 200,
            'body': json.dumps({
                **event,
                "audio_key": audio_key
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {str(e)}")
        }
