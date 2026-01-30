from diagrams import Diagram
from diagrams.generic.device import Mobile
from diagrams.saas.chat import Telegram
from diagrams.aws.mobile import APIGateway
from diagrams.aws.compute import LambdaFunction
from diagrams.aws.ml import Bedrock

with Diagram("PTB-AWS-Bedrock", show=False):
    user = Mobile("Telegram User")
    telegram = Telegram("Telegram")
    lambda_func = LambdaFunction("PTB Lambda")
    bedrock = Bedrock("Bedrock Claude 4.5")
    
    user >> telegram >> lambda_func >> bedrock
    bedrock >> lambda_func >> telegram >> user