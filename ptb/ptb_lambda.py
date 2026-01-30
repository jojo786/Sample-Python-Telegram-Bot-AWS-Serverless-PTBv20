import json
import asyncio
import boto3
import time
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
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a GenAI chatbot powered by Amazon Bedrock with real-time streaming responses, running on AWS Serverless. Ask me anything!")

#handler to send user messages to Bedrock and return AI response with streaming
async def bedrock_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id
    print(f"Bedrock chat handler called with message: {user_message}")
    
    # Generate unique draft ID
    draft_id = int(time.time() * 1000) % (2**31 - 1)
    
    # Send initial draft message
    try:
        await context.bot.send_message_draft(
            chat_id=chat_id,
            draft_id=draft_id,
            text="Thinking..."
        )
    except Exception as e:
        print(f"Draft message failed, using regular message: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Processing...")
    
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
        print("Calling Bedrock streaming API")
        # Call Bedrock with streaming
        response = bedrock.invoke_model_with_response_stream(
            modelId='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
            body=json.dumps(request_body)
        )
        
        print("Processing streaming response")
        accumulated_text = ""
        stream = response.get('body')
        
        if stream:
            for event in stream:
                chunk = event.get('chunk')
                if chunk:
                    message = json.loads(chunk.get("bytes").decode())
                    
                    if message['type'] == "content_block_delta":
                        text_chunk = message['delta'].get('text', '')
                        if text_chunk:
                            accumulated_text += text_chunk
                            
                            # Update draft every 50 characters to show progress
                            if len(accumulated_text) % 50 < len(text_chunk):
                                try:
                                    await context.bot.send_message_draft(
                                        chat_id=chat_id,
                                        draft_id=draft_id,
                                        text=accumulated_text
                                    )
                                except Exception as e:
                                    print(f"Draft update failed: {e}")
                    
                    elif message['type'] == "message_stop":
                        print("Stream completed")
                        break
        
        # Send final complete message
        if accumulated_text:
            await context.bot.send_message(chat_id=chat_id, text=accumulated_text)
            print(f"Final response sent: {len(accumulated_text)} characters")
        else:
            await context.bot.send_message(chat_id=chat_id, text="I apologize, but I couldn't generate a response. Please try again.")
        
    except Exception as e:
        print(f"Error in bedrock_chat: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"Sorry, I encountered an error: {str(e)}")

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
