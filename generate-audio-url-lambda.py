import json
import boto3

S3_BUCKET_NAME = 'ai-sales-voice-bucket'

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        body = event.get('body', {})
        
        if isinstance(body, str):
            print("Parsing body from string...")
            body = json.loads(body)

        if not isinstance(body, dict):
            raise ValueError("Invalid body format: must be JSON object")

        audio_key = body.get('audio_key')
        if not audio_key:
            raise KeyError("Missing 'audio_key' in body!")

        print(f"Audio Key: {audio_key}")

        s3_client = boto3.client('s3')
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': audio_key
            },
            ExpiresIn=900
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'audio_url': presigned_url,
                'audio_key': audio_key   # 保留 audio_key 傳給下一步
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
