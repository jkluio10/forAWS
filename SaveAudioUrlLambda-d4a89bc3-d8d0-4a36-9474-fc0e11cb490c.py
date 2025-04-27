import json
import boto3
from datetime import datetime
from urllib.parse import urlparse, unquote

S3_BUCKET_NAME = 'ai-sales-voice-bucket'

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        print("=== SaveAudioUrlLambda Start ===")
        print("Received event:", json.dumps(event))

        body = event.get('body', {})
        if isinstance(body, str):
            print("Parsing 'body' from string...")
            body = json.loads(body)

        if not isinstance(body, dict):
            raise ValueError("Invalid body format: must be JSON object")

        audio_url = body.get('audio_url')
        audio_key = body.get('audio_key')

        if not audio_url or not audio_key:
            raise KeyError("Missing 'audio_url' or 'audio_key' in body!")

        print(f"Audio URL: {audio_url}")
        print(f"Audio Key: {audio_key}")

        # 生成對應的 JSON key
        base_filename = audio_key.split('/')[-1].replace('.mp3', '.json')
        json_key = f"requestjson/{base_filename}"

        print(f"Uploading metadata JSON to S3 at {json_key}")

        metadata = {
            "audio_url": audio_url,
            "audio_key": audio_key,
            "saved_at": datetime.utcnow().isoformat() + "Z"
        }

        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=json_key,
            Body=json.dumps(metadata),
            ContentType='application/json'
        )

        print("Metadata JSON upload success!")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Audio URL saved and metadata JSON uploaded!',
                'audio_url': audio_url,
                'audio_key': audio_key,
                'json_key': json_key
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
