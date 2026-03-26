import telebot
import requests
import re
import time
import random
import string
import os
import psutil
from telebot import types
from datetime import datetime
from flask import Flask
from threading import Thread

# --- 1. BỘ GIỮ SÓNG (GIÚP RENDER CHẠY 24/7) ---
app = Flask('')
@app.route('/')
def home(): return "🧙‍♂️ Bot Pháp Sư Online 24/7 đang hoạt động!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. CẤU HÌNH (ĐÃ ĐỔI TOKEN MỚI CỦA ÔNG) ---
TOKEN = '8390962380:AAG0ngbrUGEwfv4NQv1zxuZrZdqw65QYVPA'
bot = telebot.TeleBot(TOKEN)
API_MAIL = "https://api.mail.tm"

otp_log_file = "auto_backup_otp.txt"
config_pass = "minhdeptrai"
user_data = {}

def rand_str(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# --- 3. MENU ĐA NĂNG ---
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [
        types.InlineKeyboardButton("⚡ COMBO TỰ ĐỘNG", callback_data="auto_combo"),
        types.InlineKeyboardButton("📜 Lịch Sử OTP", callback_data="view_history"),
        types.InlineKeyboardButton("📥 Tải File Backup", callback_data="download_log"),
        types.InlineKeyboardButton("📊 System Info", callback_data="sys_info"),
        types.InlineKeyboardButton("🧹 Xóa Lịch Sử", callback_data="clear_history")
    ]
    markup.add(*btns)
    return markup

# --- 4. HÀM COMBO TỰ ĐỘNG (LẤY + CANH + LƯU) ---
def auto_process_combo(cid):
    bot.send_message(cid, "🧙‍♂️ **Đang đúc Acc & Ngồi canh OTP cho ba...**", parse_mode="Markdown")
    try:
        # Bước 1: Lấy Mail mới
        res_dom = requests.get(f"{API_MAIL}/domains").json()
        domain = res_dom['hydra:member'][0]['domain']
        email = f"{rand_str()}@{domain}"
        
        requests.post(f"{API_MAIL}/accounts", json={"address": email, "password": config_pass})
        tk_res = requests.post(f"{API_MAIL}/token", json={"address": email, "password": config_pass}).json()
        token_mail = tk_res['token']
        
        user_data[cid] = {"email": email, "token": token_mail}
        bot.send_message(cid, f"📧 Acc: `{email}`\n⌛ **Đang chờ OTP (Tự quét mỗi 5s)...**", parse_mode="Markdown")
        
        # Bước 2: Vòng lặp tự quét trong 60s
        headers = {"Authorization": f"Bearer {token_mail}"}
        for _ in range(12): # 12 lần * 5s = 60s
            time.sleep(5)
            res_msg = requests.get(f"{API_MAIL}/messages", headers=headers).json()
            if res_msg['hydra:member']:
                msg_id = res_msg['hydra:member'][0]['id']
                mail_text = requests.get(f"{API_MAIL}/messages/{msg_id}", headers=headers).json()['text']
                otp = re.findall(r'\d{6}', mail_text)
                
                if otp:
                    ma_otp = otp[0]
                    now = datetime.now().strftime("%d/%m %H:%M:%S")
                    
                    # Bước 3: Tự động lưu vào máy
                    with open(otp_log_file, "a", encoding="utf-8") as f:
                        f.write(f"{email}|{config_pass}|{ma_otp} | {now}\n")
                    
                    # Bước 4: Gửi mã dạng "Chạm là Copy"
                    msg = (
                        f"✅ **CÓ OTP RỒI BA ƠI!**\n\n"
                        f"🔢 OTP (Chạm để copy): `{ma_otp}`\n"
                        f"📋 Acc: `{email}|{config_pass}`\n"
                        f"💾 Đã sao lưu vào file log."
                    )
                    return bot.send_message(cid, msg, parse_mode="Markdown", reply_markup=main_menu())
        
        bot.send_message(cid, "❌ Hết 60s chưa thấy mã. Ba hãy thử lại sau nha!", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(cid, f"❌ Lỗi Combo: {str(e)}")

# --- 5. LỆNH VÀ CALLBACK ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.reply_to(message, "🧙‍♂️ **PHÁP SƯ ONLINE 24/7 - SẴN SÀNG!**", reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['combo'])
def cmd_combo(message):
    Thread(target=auto_process_combo, args=(message.chat.id,)).start()

@bot.message_handler(commands=['tailai'])
def cmd_tailai(message):
    if os.path.exists(otp_log_file):
        with open(otp_log_file, "rb") as f: bot.send_document(message.chat.id, f)
    else: bot.reply_to(message, "⚠️ Chưa có file sao lưu.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    cid = call.message.chat.id
    if call.data == "auto_combo":
        Thread(target=auto_process_combo, args=(cid,)).start()
    elif call.data == "download_log":
        if os.path.exists(otp_log_file):
            with open(otp_log_file, "rb") as f: bot.send_document(cid, f)
        else: bot.answer_callback_query(call.id, "Chưa có file backup!")
    elif call.data == "view_history":
        if os.path.exists(otp_log_file):
            with open(otp_log_file, "r") as f:
                lines = f.readlines()[-5:]
                bot.send_message(cid, f"📜 **5 OTP GẦN NHẤT:**\n\n`{''.join(lines)}`", parse_mode="Markdown")
    elif call.data == "sys_info":
        bot.send_message(cid, f"📊 RAM: {psutil.virtual_memory().percent}% | CPU: {psutil.cpu_percent()}%")
    elif call.data == "clear_history":
        if os.path.exists(otp_log_file): os.remove(otp_log_file)
        bot.answer_callback_query(call.id, "Đã xóa lịch sử!")

if __name__ == "__main__":
    keep_alive()
    print("🚀 BOT ĐÃ LÊN ĐƯỜNG VỚI TOKEN MỚI!")
    bot.polling(none_stop=True)
