from diagrams import Diagram
from diagrams.generic.device import Mobile
from diagrams.saas.chat import Telegram
from diagrams.aws.mobile import APIGateway
from diagrams.aws.compute import LambdaFunction

with Diagram("PTB-AWS", show=False):
    Mobile("Telegram User") - Telegram("Telegram") - LambdaFunction("PTB")