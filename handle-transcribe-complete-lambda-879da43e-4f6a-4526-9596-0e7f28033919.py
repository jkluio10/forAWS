import json
import boto3

s3 = boto3.client('s3')
stepfunctions = boto3.client('stepfunctions')

# 你的 Step Function ARN
STATE_MACHINE_ARN = 'arn:aws:states:us-west-2:058128931045:stateMachine:AISalesDemo'

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # ✅ 正確解析 S3 Event 通知格式
        record = event['Records'][0]
        s3_bucket = record['s3']['bucket']['name']
        s3_key = record['s3']['object']['key']

        print(f"Received S3 bucket: {s3_bucket}, key: {s3_key}")

        # ✅ 下載 S3 裡的 transcript JSON
        response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        content = response['Body'].read()
        transcript_json = json.loads(content)

        # ✅ 抓出辨識的文字
        transcription_text = transcript_json['results']['transcripts'][0]['transcript']
        print(f"Transcription Text: {transcription_text}")

        # ✅ 從檔名切出 CustomerID
        filename = s3_key.split('/')[-1]  # 只取最後一段檔名
        customer_id = filename.split('_')[0]  # 取 "_" 前面的 ID
        print(f"CustomerID: {customer_id}")

        # ✅ 啟動 Step Function
        stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps({
                "CustomerID": customer_id,
                "transcription_text": transcription_text
            }, ensure_ascii=False)
        )

        return {
            'statusCode': 200,
            'body': 'Successfully triggered Step Function.'
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Error occurred: {str(e)}"
        }
