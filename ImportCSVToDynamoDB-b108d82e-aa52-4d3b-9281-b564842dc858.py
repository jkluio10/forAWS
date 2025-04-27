import boto3
import csv
import io

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    s3 = boto3.client('s3')


    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    print("🚀 收到 S3 上傳事件：", key)


    table_name = key.split('/')[-1].replace('.csv', '')
    table = dynamodb.Table(table_name)


    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    content = content.encode().decode('utf-8-sig')

    reader = csv.DictReader(io.StringIO(content))
    header = reader.fieldnames
    primary_key = header[0] 

    for i, row in enumerate(reader):
        if primary_key not in row or not row[primary_key]:
            print(f"❌ 第 {i+1} 筆資料缺主鍵 {primary_key}：", row)
            continue
        print(f"✅ 寫入第 {i+1} 筆資料：", row)
        table.put_item(Item=row)
    return {'status': 'success'}