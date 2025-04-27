import json
import boto3
import datetime

# 初始化 DynamoDB
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'conversation-history-table'

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # ✅ 解 Step Function多層body（確保拿到正確資料）
        if 'body' in event:
            if isinstance(event['body'], str):
                event = json.loads(event['body'])
            elif isinstance(event['body'], dict):
                event = event['body']

        # 有些情況 event本身就是字串
        if isinstance(event, str):
            event = json.loads(event)

        # 從 event 拿到資料
        customer_id = event['CustomerID']
        user_message = event['UserMessage']
        assistant_reply = event['AssistantReply']
        purchase_intent = event.get('PurchaseIntent', '未知')  # ✅ 新增：購買意願

        # 取得 table reference
        table = dynamodb.Table(TABLE_NAME)

        # 現在時間（ISO格式）
        now = datetime.datetime.utcnow()

        # 先存 user問的
        table.put_item(
            Item={
                'CustomerID': customer_id,
                'Timestamp': now.isoformat() + 'Z',
                'Role': 'user',
                'Message': user_message
            }
        )

        # 再存 assistant回的（晚一秒）
        table.put_item(
            Item={
                'CustomerID': customer_id,
                'Timestamp': (now + datetime.timedelta(seconds=1)).isoformat() + 'Z',
                'Role': 'assistant',
                'Message': assistant_reply,
                'PurchaseIntent': purchase_intent  # ✅ 新增：存進DynamoDB
            }
        )

        # ✅ 成功回傳一個結構化JSON（給text-to-speech用）
        return {
            'statusCode': 200,
            'body': json.dumps({
                'reply': assistant_reply
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {str(e)}")
        }