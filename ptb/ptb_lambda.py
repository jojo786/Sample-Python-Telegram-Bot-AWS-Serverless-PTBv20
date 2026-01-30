import json
import asyncio
import boto3
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

#For demo purposes only, you can configure your Telegram Bot Token here:
#For security, it's safer to store the bot token using:
#- Environment variables: os.environ.get('TELEGRAM_BOT_TOKEN')
#- AWS SSM Parameter Store: boto3.client('ssm').get_parameter(Name='/bot/token', WithDecryption=True)
#- AWS Secrets Manager: boto3.client('secretsmanager').get_secret_value(SecretId='telegram-bot-token')
TELEGRAM_TOKEN = "INSERT TELEGRAM TOKEN"

# Initialize Bedrock client
bedrock = boto3.client('bedrock-runtime')

#/start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start command received")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a Telegram GenAI chatbot powered by Amazon Bedrock and Python Telegram Bot (PTB) library, running on AWS Serverless. Ask me anything!")

#handler to send user messages to Bedrock and return AI response
async def bedrock_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    print(f"Bedrock chat handler called with message: {user_message}")
    
    # Prepare request for Claude
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    
    try:
        print("Calling Bedrock API")
        # Call Bedrock
        response = bedrock.invoke_model(
            modelId='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
            body=json.dumps(request_body)
        )
        
        print("Parsing Bedrock response")
        # Parse response
        response_body = json.loads(response['body'].read())
        ai_response = response_body['content'][0]['text']
        print(f"AI response: {ai_response[:100]}...")
        
        # Send AI response back to user
        await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_response)
        print("Response sent to user")
        
    except Exception as e:
        print(f"Error in bedrock_chat: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Sorry, I encountered an error: {str(e)}")

#lambda handler, which is what will be invoked by AWS Lambda, which calls main
def lambda_handler(event, context):
    print(f"Lambda handler called with event: {event}")
    
    # Create new event loop for each invocation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(main(event, context))
    finally:
        loop.close()

async def main(event, context):
    print("Main function started")
    
    # Create application inside main to avoid event loop conflicts
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    bedrock_chat_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), bedrock_chat)
    application.add_handler(bedrock_chat_handler)
    
    try:    
        print("Initializing application")
        await application.initialize()
        print("Processing update")
        await application.process_update(
            Update.de_json(json.loads(event["body"]), application.bot)
        )
        print("Update processed successfully")
        return {
            'statusCode': 200,
            'body': 'Success'
        }

    except Exception as exc:
        print(f"Error in main: {exc}")
        return {
            'statusCode': 500,
            'body': 'Failure'
        }
    finally:
        # Clean up application
        try:
            await application.shutdown()
        except:
            pass
