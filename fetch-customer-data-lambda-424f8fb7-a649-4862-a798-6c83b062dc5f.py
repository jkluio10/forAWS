import json
import boto3
from boto3.dynamodb.conditions import Key

# 初始化 DynamoDB client
dynamodb = boto3.resource('dynamodb')

# 資料表名稱
CUSTOMER_TABLE = 'customer-table'
HISTORY_TABLE = 'conversation-history-table'  # ✅ 歷史紀錄
PRODUCT_TABLE = 'product-table'
CONVERSATION_TABLE = 'conversation-table'
SALES_TABLE = 'sales-table'

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # ✅ 如果是 API Gateway 事件格式，有包一層 body，要解開
        if 'body' in event:
            if isinstance(event['body'], str):
                event = json.loads(event['body'])

        customer_id = event.get('CustomerID')
        if not customer_id:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing CustomerID.')
            }

        # Step 1: 查詢客戶資料
        customer_table = dynamodb.Table(CUSTOMER_TABLE)
        customer_response = customer_table.get_item(Key={'CustomerID': customer_id})

        if 'Item' not in customer_response:
            return {
                'statusCode': 404,
                'body': json.dumps(f'CustomerID {customer_id} not found in customer-table.')
            }

        customer_data = customer_response['Item']

        # Step 2: 查詢最近10筆歷史聊天
        history_table = dynamodb.Table(HISTORY_TABLE)
        history_response = history_table.query(
            KeyConditionExpression=Key('CustomerID').eq(customer_id),
            ScanIndexForward=False,  # 最近的排前面
            Limit=10
        )
        chat_history = history_response.get('Items', [])
        chat_history = sorted(chat_history, key=lambda x: x['Timestamp'])  # 再依 Timestamp 正序排列

        # Step 3: 撈出產品清單
        product_table = dynamodb.Table(PRODUCT_TABLE)
        product_response = product_table.scan()
        products = product_response.get('Items', [])

        # Step 4: 撈出對話範本
        conversation_template_table = dynamodb.Table(CONVERSATION_TABLE)
        conversation_template_response = conversation_template_table.scan()
        conversation_templates = conversation_template_response.get('Items', [])

        # Step 5: 撈出銷售話術
        sales_table = dynamodb.Table(SALES_TABLE)
        sales_response = sales_table.scan()
        sales_templates = sales_response.get('Items', [])

        # Step 6: 組成回傳資料
        return {
            'statusCode': 200,
            'body': json.dumps({
                'customer': customer_data,
                'chat_history': chat_history,
                'products': products,
                'conversation_templates': conversation_templates,
                'sales_templates': sales_templates
            }, ensure_ascii=False)
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {str(e)}")
        }
