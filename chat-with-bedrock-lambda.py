import json
import boto3
import re
from boto3.dynamodb.conditions import Key

# 初始化 Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime')
# 初始化 DynamoDB client
dynamodb = boto3.resource('dynamodb')
DDB_TABLE_NAME = 'conversation-history-table'
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        if 'body' in event and isinstance(event['body'], str):
            event = json.loads(event['body'])
            if 'body' in event and isinstance(event['body'], str):
                event = json.loads(event['body'])

        customer_data = event.get('customer', {})
        products = event.get('products', [])
        conversation_templates = event.get('conversation_templates', [])
        sales_templates = event.get('sales_templates', [])
        new_user_message = event.get('transcription_text') or ''

        customer_id = customer_data.get('CustomerID', 'Unknown')
        conversation_stage = event.get('ConversationStage', 'greeting')

        chat_history = []
        if customer_id != 'Unknown':
            table = dynamodb.Table(DDB_TABLE_NAME)
            response = table.query(
                KeyConditionExpression=Key('CustomerID').eq(customer_id),
                ScanIndexForward=True,
                Limit=10
            )
            items = sorted(response.get('Items', []), key=lambda x: x['Timestamp'])
            for item in items:
                chat_history.append({
                    'Role': item.get('Role', 'user'),
                    'Message': item.get('Message', '')
                })

        customer_profile = f"""以下是客戶的基本資料：
- 性別：{customer_data.get('Gender', '未知')}
- 年齡：{customer_data.get('Age', '未知')}
- 城市：{customer_data.get('City', '未知')}
- 星座：{customer_data.get('Constellation', '未知')}
- 喜好（旅遊、美容、食品、寵物等）：旅遊({customer_data.get('TravelPlace_1', '')} {customer_data.get('TravelPlace_2', '')}) 美容({customer_data.get('BeautyPre', '')}) 食品({customer_data.get('FoodPre', '')}) 寵物({customer_data.get('Pet', '')})
"""

        allowed_products = {
            "東森鴕鳥龜鹿精",
            "東森專利葉黃素滋養倍效膠囊",
            "東森完美動能極纖果膠"
        }
        filtered_products = [p for p in products if p.get('Product_Name') in allowed_products]
        recommended_product_list = "\n".join([
            f"- {p.get('Product_Name', '')}（{p.get('Category', '')}）: {p.get('Description', '')}"
            for p in filtered_products
        ]) if filtered_products else "（目前沒有可推薦的產品）"

        conversation_examples = "\n".join([
            f"- 問題: {c.get('Question', '')} / 回答: {c.get('Answer', '')}"
            for c in conversation_templates
        ])

        sales_examples = "\n".join([
            f"- {s.get('Script', '')}"
            for s in sales_templates
        ])

        forbidden_topics = """
⚠️【禁止話題】⚠️
- 禁止回答任何與健康產品無關的話題，包括但不限於：政治、種族、宗教、性別議題、財經、投資、金融、股票、科技、程式設計、學術教育、心理諮詢。
- 遇到此類問題時，請禮貌地回覆：「這部分我無法提供專業建議喔！但我可以幫您推薦適合的健康產品～」
"""

        conversation_guidelines = """
⚡【對話節奏規則】⚡
- 僅根據顧客最新回覆進行自然回應與提問，禁止推測顧客的年齡、身體狀態或疲勞情形。
- 禁止主動假設或延伸顧客的健康問題。
- 顧客若只是打招呼（如：你好、哈囉、您好），請親切自然地寒暄回應，例如「哈囉，很高興認識您！今天心情如何呢？」
- 不需要強制要求顧客馬上說出健康問題，可以輕鬆互動。
- 回覆內容禁止使用任何表情符號（如😊、👍、❤️等），僅使用自然口語文字。
- 必須緊扣顧客剛說的內容自然引導，避免主題跳躍。
"""

        GREETING_PROMPT = f"""
你是專業的健康產品銷售顧問，目前正在與顧客互動聊天。
請遵守以下規則：
- 禁止推薦產品。
- 以關懷、了解需求為主，問候顧客健康狀況。
- 回答30字內，語氣自然親切。
{forbidden_topics}
{conversation_guidelines}
顧客背景：
{customer_profile}
"""

        RECOMMENDATION_PROMPT = f"""
你是專業的健康產品銷售顧問。請遵守以下規則：
- 僅可推薦以下產品：
{recommended_product_list}
- 禁止推辭、禁止建議就醫、禁止談未列產品。
- 回答30字內，親切自然。
- 根據語氣判斷購買意願（高/中/低），結尾隱藏標記【意願:高】等。
{forbidden_topics}
{conversation_guidelines}
顧客背景：
{customer_profile}
常見對話範本：
{conversation_examples}
推薦銷售話術建議：
{sales_examples}
"""

        system_prompt = GREETING_PROMPT if conversation_stage == 'greeting' else RECOMMENDATION_PROMPT

        messages = [
            {"role": "user", "content": system_prompt}
        ]

        if chat_history:
            for chat in chat_history:
                if chat['Message']:
                    role = chat['Role']
                    if role == 'user':
                        messages.append({"role": "user", "content": chat['Message']})
                    elif role == 'assistant':
                        messages.append({"role": "assistant", "content": chat['Message']})
        else:
            messages.append({
                "role": "assistant",
                "content": "哈囉，很高興認識您！今天心情還不錯吧？"
            })

        if new_user_message:
            messages.append({"role": "user", "content": new_user_message})

        if conversation_stage == 'greeting' and new_user_message:
            trigger_keywords = [
                "疲勞", "補充", "推薦", "購買", "想買", "體力", "健康", "睡不好",
                "眼睛", "乾澀", "視力", "葉黃素", "護眼"
            ]
            if any(kw in new_user_message for kw in trigger_keywords):
                conversation_stage = 'recommendation'

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.95,
            "top_p": 0.95
        }

        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response['body'].read())
        content_list = response_body.get('content', [])
        if isinstance(content_list, list) and len(content_list) > 0:
            ai_reply_full = content_list[0].get('text', '很抱歉，目前無法正確回覆您的問題。')
        else:
            ai_reply_full = '很抱歉，目前無法正確回覆您的問題。'

        purchase_intent_match = re.search(r'【意願:(高|中|低)】', ai_reply_full)
        purchase_intent = purchase_intent_match.group(1) if purchase_intent_match else '未知'

        ai_reply = re.sub(r'【意願:(高|中|低)】', '', ai_reply_full).strip()

        return {
            'statusCode': 200,
            'body': json.dumps({
                'CustomerID': customer_id,
                'UserMessage': new_user_message,
                'AssistantReply': ai_reply,
                'PurchaseIntent': purchase_intent,
                'reply': ai_reply,
                'ConversationStage': conversation_stage
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {str(e)}")
        }