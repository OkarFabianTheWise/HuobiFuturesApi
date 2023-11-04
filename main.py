from HuobiDMService import HuobiDM
import requests
import os
from telebot import TeleBot
import telebot
import re
from flask import Flask, request
app = Flask(__name__)
from environs import Env
env = Env()
env.read_env('.env')
from database import Database

chat = 'telegram_chat_id'
db = Database()

### import variables from .env file. you can set it from there
BOT_TOKEN = env("BOT_TOKEN")
ACCESS_KEY = env("ACCESS_KEY")
SECRET_KEY = env("SECRET_KEY")

bot = TeleBot(token=BOT_TOKEN)

invest = 520 # position size

#### input huobi dm url

URL = f'https://api.hbdm.com'

dm = HuobiDM(URL, ACCESS_KEY, SECRET_KEY)

def get_price(symbol):
    try:
        url = f'https://api.huobi.pro/market/trade?symbol={symbol}'
        res = requests.get(url)
        return res.json()
    except Exception as z:
        return None

def long_trade(coin):
    try:
        symbol = coin.lower()
        price = get_price(f"{symbol}usdt")['tick']['data'][0]['price']
        cont_size = dm.swap_contract_info(f'{coin}-USDT')['data'][0]['contract_size']
        intendedAmount = invest*10
        csp = cont_size*price
        volume = int(intendedAmount / csp)
        decimals = len(str(price).split('.')[1])
        if price > 4:
            decimals = 1
        inc = 0.05 * price
        TP = price + inc
        dec = 0.07 * price
        SL = price - dec
        TP_rounded = round(TP, decimals)
        SL_rounded = round(SL, decimals)
        order = dm.linear_swap_order(f"{coin}-USDT", volume, "buy", "open", 10, TP_rounded, SL_rounded)
        print('order', order)
        status = order.get('status')
        red = f"*Order Placed*\n\n*Asset:* {coin}\n*Price:* {price}\n*TP:* {TP_rounded}\n*SL:* {SL_rounded}\n*Leverage: {10}*\n*Volume:* {volume}\n\n*Status:* {status}"
        if status == 'ok':
            order_id_str = order['data']['order_id_str']
            print(order_id_str)
            db.add_trade(symbol, order_id_str, 'sell')
            return red
        else:
            return order.get('err_msg')
    except Exception as x:
        print('short err', x)
    
def short_trade(coin):
    try:
        symbol = coin.lower()
        price = get_price(f"{symbol}usdt")['tick']['data'][0]['price']
        cont_size = dm.swap_contract_info(f'{coin}-USDT')['data'][0]['contract_size']
        intendedAmount = invest*10
        csp = cont_size*price
        volume = int(intendedAmount / csp)
        decimals = len(str(price).split('.')[1])
        if price > 4:
            decimals = 1
        inc = 0.07 * price
        SL = price + inc
        dec = 0.05 * price
        TP = price - dec
        TP_rounded = round(TP, decimals)
        SL_rounded = round(SL, decimals)
        order = dm.linear_short_order(f"{coin}-USDT", volume, "sell", "open", 10, TP_rounded, SL_rounded)
        print('order', order)
        status = order.get('status')
        if status == 'ok':
            order_id_str = order['data']['order_id_str']
            db.add_trade(symbol, order_id_str, 'buy')
            red = f"*Order Placed*\n\n*Asset:* {coin}\n*Price:* {price}\n*TP:* {TP_rounded}\n*SL:* {SL_rounded}\n*Leverage: {10}*\n*Volume:* {volume}\n\n*Status:* {status}"
            return red
        else:
            return order.get('err_msg')
    except Exception as x:
        print('short err', x)
    

# close trade function
def close(coin, order_id, direction):
    try:
        volume = dm.swap_order_info(f'{coin}-USDT', order_id)['data']['volume']
        print("volume", volume)
        close = dm.linear_closing(f"{coin}-USDT", int(volume), direction, "close", 10)
        print("close", close)
        status = close.get('status')
        if status == 'ok':
            return "Trade Canceled"
        else:
            return close.get('err_msg')
    except Exception as x:
        print('close err', x)
        return "*Sorry! No trade open for this Pair*"
    
# ping bot on heroku
@bot.message_handler(commands=['speak'])
def help_command(message):
    bot.reply_to(message, f"ser, i'm online")

@bot.message_handler(content_types=['text'])
def sell_searcher(message):
    try:
        message_text = message.text
        message_text = message_text.lower()

        # Define a regular expression pattern to match the asset
        pattern = r'#(\w+)'

        # Use re.search to find the first match in the message text
        match = re.search(pattern, message_text) #re.IGNORECASE)

        if match:
            search_asset = match.group(1)  # Extract and convert asset to uppercase
            symbol = search_asset
            coin = search_asset.upper()
            
            if "cancel" in message_text and "short" in message_text:
                action = "sell"
            elif "cancel" in message_text and "long" in message_text:
                action = "sell"
            elif "close" in message_text and "short" in message_text:
                action = "sell"
            elif "close" in message_text and "short" in message_text:
                action = "sell"
            elif "close" in message_text and "long" in message_text:
                action = "sell"
            elif "buy" in message_text and "sell" in message_text:
                action = "buy"
            elif "buy" in message_text and "long" in message_text:
                action = "buy"
            elif "buy" in message_text or "long" in message_text:
                action = "buy"
            elif "open" in message_text and "long" in message_text:
                action = "buy"
            elif "open" in message_text and "short" in message_text:
                action = "short"
            elif "buy" in message_text and "short" in message_text:
                action = "short"
            elif "short" in message_text:
                action = "short"
            elif "cancel" in message_text or "close" in message_text or "closed" in message_text or "canceled" in message_text:
                action = "sell"
            else:
                action = ""
                
            if action == 'buy':
                order = long_trade(coin)
                bot.send_message(chat, order, parse_mode='Markdown')
            elif action == "short":
                order = short_trade(coin)
                bot.send_message(chat, order, parse_mode='Markdown')
            elif action == "sell":
                res = db.get_trades_by_asset(symbol)
                order_id = res[0][1]
                direction = res[0][2]
                cl = close(coin, order_id, direction)
                bot.send_message(chat, cl, parse_mode='Markdown')
            else:
                pass
        else:
            pass
    except Exception as x:
        pass

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    # Access the text part of the message if it exists
    message_text = message.caption.lower()
    if message_text:
        try:
            # Define a regular expression pattern to match the asset
            pattern = r'#(\w+)'

            # Use re.search to find the first match in the message text
            match = re.search(pattern, message_text)#, re.IGNORECASE)

            if match:
                search_asset = match.group(1)  # Extract and convert asset to uppercase
                symbol = search_asset
                coin = search_asset.upper()
                if "cancel" in message_text or "close" in message_text or "closed" in message_text or "canceled" in message_text:
                    action = "sell"
                elif "cancel" in message_text and "short" in message_text:
                    action = "sell"
                elif "cancel" in message_text and "long" in message_text:
                    action = "sell"
                elif "close" in message_text and "short" in message_text:
                    action = "sell"
                elif "close" in message_text and "short" in message_text:
                    action = "sell"
                elif "close" in message_text and "long" in message_text:
                    action = "sell"
                elif "buy" in message_text and "sell" in message_text:
                    action = "buy"
                elif "buy" in message_text and "long" in message_text:
                    action = "buy"
                elif "buy" in message_text or "long" in message_text:
                    action = "buy"
                elif "open" in message_text and "long" in message_text:
                    action = "buy"
                elif "open" in message_text and "short" in message_text:
                    action = "short"
                elif "buy" in message_text and "short" in message_text:
                    action = "short"
                elif "short" in message_text:
                    action = "short"
                else:
                    action = ""
                    
                if action == "buy":
                    order = long_trade(coin)
                    bot.send_message(chat, order, parse_mode='Markdown')
                elif action == "short":
                    order = short_trade(coin)
                    bot.send_message(chat, order, parse_mode='Markdown')
                elif action == "sell":
                    res = db.get_trades_by_asset(symbol)
                    order_id = res[0][1]
                    direction = res[0][2]
                    cl = close(coin, order_id, direction)
                    bot.send_message(chat, cl, parse_mode='Markdown')
                else:
                    pass
            else:
                pass
        except Exception as z:
            print("photo extract", z)
    else:
        pass

@app.route('/webhook' + BOT_TOKEN, methods=['POST'])
def handle_telegram_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

def webhook(): 
    bot.remove_webhook()
    bot.set_webhook(url='heroku-app-url/webhook' + BOT_TOKEN)
    return "!", 200

if __name__ == '__main__':
    webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
