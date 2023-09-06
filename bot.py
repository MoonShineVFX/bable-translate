import requests,json
from flask import Flask, request, abort,render_template,jsonify,current_app
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MemberJoinedEvent,MessageEvent, TextMessage, TextSendMessage,TemplateSendMessage, ImageCarouselTemplate ,ImageCarouselColumn ,MessageAction,URIAction,PostbackEvent,ButtonsTemplate,PostbackTemplateAction,CarouselTemplate,CarouselColumn,FlexSendMessage,ImageSendMessage,VideoSendMessage,PostbackAction,AudioMessage)
import logging,os

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['LINE_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_ACCESS_SECRET'])
google_api_key = os.getenv("GOOGLE_TRANSLATION_API_KEY")



def detect(text):
    params = {
        'key': google_api_key,
        'q': text
    }
    api_endpoint = 'https://translation.googleapis.com/language/translate/v2/detect'
    response = requests.get(api_endpoint, params=params)
    data = response.json()
    language = data['data']['detections'][0][0]['language']
    return language

def googletranslate(source,target,text):
    params = {
        'key': google_api_key,
        'q': text,
        'source': source,
        'target': target
    }
    api_endpoint = 'https://translation.googleapis.com/language/translate/v2'
    response = requests.get(api_endpoint, params=params)
    data = response.json()
    translated_text = data['data']['translations'][0]['translatedText']
    return translated_text

@app.route("/")
def home():
    return "hi~~~"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MemberJoinedEvent)
def handle_membermessage(event):
    if (event.type=="memberJoined"):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="嗨！我是 Babel 一個翻譯機器人~"))


@handler.add(MessageEvent)
def handle_message(event):
    if event.message.type=="text" :
        if event.source.type=="group" or event.source.type=="room" or event.source.type=='user':
            language = detect(event.message.text)
            if language == 'zh-CN' or language == 'zh-TW':
                translated_text = googletranslate(language,'en',event.message.text)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))
            elif language == 'en':
                translated_text = googletranslate(language,'zh-TW',event.message.text)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))


        

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000,debug=True)
