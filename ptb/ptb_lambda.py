import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

#For demo purposes only, you can configure your Telegram Bot Token here:
#For security, it's safer to store the bot token using:
#- Environment variables: os.environ.get('TELEGRAM_BOT_TOKEN')
#- AWS SSM Parameter Store: boto3.client('ssm').get_parameter(Name='/bot/token', WithDecryption=True)
#- AWS Secrets Manager: boto3.client('secretsmanager').get_secret_value(SecretId='telegram-bot-token')
application = ApplicationBuilder().token("YOUR-TELEGRAM-TOKEN-HERE").build()

#/start handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot running on AWS Serverless, please talk to me!")

#handler to echo back all messages back to telegram
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

#lambda handler, which is what will be invoked by AWS Lambda, which calls main
def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(main(event, context))

async def main(event, context):
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    application.add_handler(echo_handler)
    
    try:    
        await application.initialize()
        await application.process_update(
            Update.de_json(json.loads(event["body"]), application.bot)
        )
    
        return {
            'statusCode': 200,
            'body': 'Success'
        }

    except Exception as exc:
        return {
            'statusCode': 500,
            'body': 'Failure'
        }
    
   

