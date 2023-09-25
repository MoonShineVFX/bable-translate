import requests,json
from flask import Flask, request, abort,render_template,jsonify,current_app,send_file
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MemberJoinedEvent,MessageEvent, TextMessage, TextSendMessage,TemplateSendMessage, ImageCarouselTemplate ,ImageCarouselColumn ,MessageAction,URIAction,PostbackEvent,ButtonsTemplate,PostbackTemplateAction,CarouselTemplate,CarouselColumn,FlexSendMessage,ImageSendMessage,VideoSendMessage,PostbackAction,AudioMessage,AudioSendMessage)
import logging,os,time
import openai
import base64
from mutagen.mp3 import MP3
import boto3
import sqlite3


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['LINE_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_ACCESS_SECRET'])
google_api_key = os.getenv("GOOGLE_TRANSLATION_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
google_speech_api_key = os.getenv("GOOGLE_TEXT_TO_SPEECH_API_KEY")
app_url = os.getenv("APP_URL")

r2_access_key_id = os.getenv("R2_ACCESS_KEY_ID")
r2_secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
bucket_name = os.getenv("BUCKET_NAME")
r2_url = os.getenv("R2_URL")
s3 = boto3.resource('s3',endpoint_url = r2_url,aws_access_key_id = r2_access_key_id,aws_secret_access_key = r2_secret_access_key)

langlist={"th": "Thai",
          "ja":"Japanese",
          "en": "English"
          }

def upload_file_to_r2(file_path):
    s3_file_path = file_path
    s3_file_path = s3_file_path.replace('\\', '/')
    bucket = s3.Bucket(bucket_name)
    bucket.upload_file(file_path, s3_file_path)
    return app_url+file_path


def text2speech(text,languageCode,file_path):
    api_endpoint = 'https://texttospeech.googleapis.com/v1/text:synthesize?key=' + google_speech_api_key
    data = {
        "input": {
            "text": text  
        },
        "voice": {
            "languageCode": languageCode,  
            "ssmlGender": "FEMALE"  
        },
        "audioConfig": {
            "audioEncoding": "MP3",  
            "sampleRateHertz": 16000  
        }
    }
    response = requests.post(api_endpoint, json=data)
    response_data = json.loads(response.text)
    audio_content = response_data["audioContent"]
    audio_bytes = base64.b64decode(audio_content)
    with open(file_path, "wb") as audio_file:
        audio_file.write(audio_bytes)
    audio = MP3(file_path)
    duration = audio.info.length
    return file_path,duration

def openaispeech2text(filepath):
    audio_file= open(filepath, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    #transcript = openai.Audio.translate("whisper-1", audio_file)
    logger.info(f'#######{transcript["text"]}')
    return transcript["text"]


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
    logger.info(f'googletranslate data:{data}')
    translated_text = data['data']['translations'][0]['translatedText']
    translated_text = translated_text.replace("&#39;","'")
    logger.info(f'#######{translated_text}')
    return translated_text

def check_lang_target(groupid):
    try:
        conn = sqlite3.connect('babel.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT lang FROM setting where groupid='{groupid}'")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows == []:
            return 'th'
        else:
            for row in rows:
                return row[0]
    except Exception as e :
        logger.error(f'check_lang_target e:{e}')
        cursor.close()
        conn.close()

def update_lang_target(groupid,lang):
    try:
        conn = sqlite3.connect('babel.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT lang FROM setting where groupid='{groupid}'")

        rows = cursor.fetchall()
        if rows == []:
            cursor.execute('INSERT INTO setting (groupid, lang) VALUES (?, ?)', (groupid, lang))        
            conn.commit()
        else:
            cursor.execute('UPDATE setting SET lang = ? WHERE groupid = ?', (lang, groupid))
            conn.commit()
        cursor.close()
        conn.close()
    except Exception as e :
        cursor.execute('INSERT INTO setting (groupid, lang) VALUES (?, ?)', (groupid, lang))
        conn.commit()
        logger.error(f'e:{e}')
        cursor.close()
        conn.close()
    

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

@app.route('/audio/<filename>')
def downloadaudio(filename):
    file_path = filename
    try:
        return send_file(file_path, mimetype='audio/mp3')
    except Exception as e:
        logger.error(f'e:{e}')

@handler.add(MemberJoinedEvent)
def handle_membermessage(event):
    if (event.type=="memberJoined"):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="嗨！我是Moonshot翻譯機器人,能夠將中文翻譯成英文、日文或泰文。\n\n可使用/setting指令切換\nEx. /setting ja\n\n支援清單:\nth: Thai\nja: Japanese\nen: English\n"))


@handler.add(MessageEvent)
def handle_message(event):
    if event.source.type=="group":
        groupid = str(event.source.group_id)
    elif event.source.type=="room":
        groupid = str(event.source.room_id)
    else:
        groupid = str(event.source.user_id)

    if (event.message.type == "audio"):
        
        UserSendAudio = line_bot_api.get_message_content(event.message.id)
        path=  event.message.id + '.m4a'

        with open(path, 'wb') as fd:
            for chunk in UserSendAudio.iter_content():
                fd.write(chunk)
        
        text = openaispeech2text(path)
        language = detect(text)
        logger.info(f"language:{language}")
        target = check_lang_target(groupid)
        if language == 'zh-CN' or language == 'zh-TW':
            translated_text = googletranslate(language,target,text)
            file,duration = text2speech(translated_text,target,event.message.id+'_t.mp3')
            audio_url = upload_file_to_r2(file)
            line_bot_api.reply_message(event.reply_token, AudioSendMessage(original_content_url=audio_url, duration=duration*1000))
        elif language == 'en':
            translated_text = googletranslate(language,'zh-TW',text)
            file,duration = text2speech(translated_text,'zh-TW',event.message.id+'_t.mp3')
            audio_url = upload_file_to_r2(file)
            line_bot_api.reply_message(event.reply_token, AudioSendMessage(original_content_url=audio_url, duration=duration*1000))
        elif language == 'th':
            translated_text = googletranslate(language,'zh-TW',text)
            file,duration = text2speech(translated_text,'zh-TW',event.message.id+'_t.mp3')
            audio_url = upload_file_to_r2(file)
            line_bot_api.reply_message(event.reply_token, AudioSendMessage(original_content_url=audio_url, duration=duration*1000))
        elif language == 'ja':
            translated_text = googletranslate(language,'zh-TW',text)
            file,duration = text2speech(translated_text,'zh-TW',event.message.id+'_t.mp3')
            audio_url = upload_file_to_r2(file)
            line_bot_api.reply_message(event.reply_token, AudioSendMessage(original_content_url=audio_url, duration=duration*1000))
        try:
            os.remove(path)
            time.sleep(10)
            os.remove(file)
        except:
            logger.info(f'找不到檔案')

    elif event.message.type=="text" :
        if event.source.type=="group" or event.source.type=="room" or event.source.type=='user':
            if event.message.text.lower().startswith('/setting '):
                lang = event.message.text.lower().replace('/setting ','')
                if lang in langlist:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=langlist[lang]))
                    update_lang_target(groupid,lang)
                    target = check_lang_target(groupid)
                else:
                    txt = 'Currently supported languages,\nth: Thai \nja: Japanese\nen: English\n'
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=txt))

            else:
                language = detect(event.message.text)
                target = check_lang_target(groupid)
                if language == 'zh-CN' or language == 'zh-TW':
                    translated_text = googletranslate(language,target,event.message.text)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))
                elif language == 'en':
                    translated_text = googletranslate(language,'zh-TW',event.message.text)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))
                elif language == 'th':
                    translated_text = googletranslate(language,'zh-TW',event.message.text)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))
                elif language == 'ja':
                    translated_text = googletranslate(language,'zh-TW',event.message.text)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))

        

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000,debug=True)
