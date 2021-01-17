import sys
import json
import os
from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
   CarouselColumn, CarouselTemplate, FollowEvent,
   LocationMessage, MessageEvent, TemplateSendMessage,
   TextMessage, TextSendMessage, UnfollowEvent, URITemplateAction
)
import requests
import urllib.parse

app = Flask(__name__)

 #環境変数取得 
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]
YOUR_HOTPEPPER_API = os.environ["YOUR_HOTPEPPER_API"]

 #APIの設定 
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

 #その他 
no_hit_message = "近くにテイクアウト可能なお店はないようです"
DAMMY_URL = "https://i.pinimg.com/originals/6f/d8/5d/6fd85d362e61b473a9debc7ef78596c9.png"

 #テスト用
@app.route("/")
def hello_world():
   return "hello world!"

 #Webhookからのリクエストをチェック 
@app.route("/callback", methods=['POST'])
def callback():
   signature = request.headers['X-Line-Signature']
   body = request.get_data(as_text=True)
   app.logger.info("Request body: " + body)
   try:
       handler.handle(body, signature)
   except InvalidSignatureError:
       abort(400)
   return 'OK'

 #ホットペッパー検索 
def search_shop(lat, lng):
   url = "https://webservice.recruit.co.jp/hotpepper/gourmet/v1/"
   params = {}
   params['key'] = YOUR_HOTPEPPER_API
   params['lat'] = lat
   params['lng'] = lng
   params['range'] = 3
   params['keyword'] = "テイクアウト"
   params['lunch'] = 1
   params['order'] = 4
   response = requests.get(url, params)
   results = response.json()
   if "error" in results:
       if "message" in results:
           raise Exception("{}".format(results["message"]))
       else:
           raise Exception(DEF_ERR_MESSAGE)
   total_hit_count = results.get("total_hit_count", 0)
   if total_hit_count < 1:
       raise Exception(no_hit_message)
   return results

 #メイン処理
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
   # 空のリストを作成
   list = []

   # LINEからの位置情報で緯度と経度を受け取る
   user_lat = event.message.latitude
   user_longit = event.message.longitude
   shop_result = search_shop(user_lat, user_longit)

   for shop in shop_result.get("shop"):
      # 店舗画像
       photo = shop.get("photo", {})
       pc = photo.get("pc", {})
       l = pc.get("l", "")
       if l == "":
           l = DAMMY_URL
      # 掲載店名
       name = shop.get("name", "")
      # 店舗URL
       urls = shop.get("urls", "")
      #  PR文
       catch = shop.get("catch", "")
      #  pr_short = "以下、内容\n" + pr.get("pr_short", "")
      #  if len(pr_short) >= 60:
      #      pr_short = pr_short[:56] + "…"
      #  携帯用交通アクセス
      #  mobile_access = shop.get("mobile_access", "")
   
   
       result_dict = {
               "thumbnail_image_url": l,
               "title": name,
               "text": catch,
               "actions": {
                   "label": "ホットペッパーで見る",
                   "uri": urls
               }
           }
       list.append(result_dict)
   print(list)

   columns = [
       CarouselColumn(
           thumbnail_image_url=column["thumbnail_image_url"],
           title=column["title"],
           text=column["text"],
           actions=[
               URITemplateAction(
                   label=column["actions"]["label"],
                   uri=column["actions"]["uri"],
               )
           ]
       )
       for column in list
   ]

   messages = TemplateSendMessage(
       alt_text="お近くのテイクアウト可能なお店について連絡しました。",
       template=CarouselTemplate(columns=columns),
   )
   line_bot_api.reply_message(event.reply_token, messages=messages)

 #友達追加時イベント 
@handler.add(FollowEvent)
def handle_follow(event):
   line_bot_api.reply_message(
       event.reply_token,
       TextSendMessage(text='友達追加ありがとう!'))


if __name__ == "__main__":
   port = int(os.getenv("PORT"))
   app.run(host="0.0.0.0", port=port)