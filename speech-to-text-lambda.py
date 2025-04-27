import json
import boto3
import uuid

s3 = boto3.client('s3')
transcribe = boto3.client('transcribe')

S3_BUCKET_NAME = 'ai-sales-voice-bucket'

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        record = event['Records'][0]
        s3_bucket = record['s3']['bucket']['name']
        s3_key = record['s3']['object']['key']

        filename = s3_key.split('/')[-1]
        filename_without_extension = filename.rsplit('.', 1)[0]
        if '-' in filename_without_extension:
            customer_id = filename_without_extension.split('-')[-1]
        else:
            raise ValueError("CustomerID not found after '-' in filename")

        job_id = str(uuid.uuid4())
        job_name = f"transcribe-{customer_id}-{job_id}"
        media_uri = f"s3://{s3_bucket}/{s3_key}"
        output_key = f"transcripts/{customer_id}_{job_id}.json"

        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat='flac',  # ★ 優化成flac
            LanguageCode='zh-TW',
            OutputBucketName=s3_bucket,
            OutputKey=output_key,
            Settings={                   # ★ 加上這一段設定
                'ShowSpeakerLabels': False,
                'ChannelIdentification': False
            }
        )

        print(f"Started transcription job: {job_name}")
        print(f"Media URI: {media_uri}")
        print(f"Output Key: {output_key}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Started transcription job successfully',
                'job_name': job_name,
                'output_key': output_key
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
