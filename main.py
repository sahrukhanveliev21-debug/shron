import asyncio
import sqlite3
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import SessionPasswordNeededError
from flask import Flask, request, jsonify
import threading
import time

# Environment variables
API_ID = int(os.getenv('API_ID', '2040'))
API_HASH = os.getenv('API_HASH', 'b18441a1ff607e10a989891a5462e627')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8351363618:AAHmq7zZSZSeLaylwKjfGzgku1DUlVZuekE')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '5454585281').split(',')))

os.makedirs('sessions', exist_ok=True)
conn = sqlite3.connect('accounts.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session_name TEXT)')
conn.commit()

app = Flask(__name__)
bot = None
clients = {}
connecting = set()

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start_account(phone, session_name):
    """Start account with flood protection"""
    if phone in connecting:
        return False
    
    connecting.add(phone)
    try:
        client = TelegramClient(f'sessions/{session_name}', API_ID, API_HASH)
        await client.connect()
        await client.start(phone=phone)
        clients[phone] = client
        print(f'✅ {phone} запущен')
        
        @client.on(events.NewMessage)
        async def check(event):
            try:
                auths = await client(GetAuthorizationsRequest())
                for auth in auths.authorizations:
                    if not auth.current:
                        await bot.send_message(
                            ADMIN_IDS[0],
                            f'⚠️ НОВАЯ СЕССИЯ!\n\n📞 {phone}\n📱 {auth.device_model}\n💻 {auth.platform}\n🌐 {auth.ip}\n📍 {auth.country}\n🕐 {datetime.fromtimestamp(auth.date_created).strftime("%d.%m.%Y %H:%M")}',
                            buttons=[[
                                Button.inline("🚫 КИНУТЬ", f"kick_{phone}_{auth.hash}"),
                                Button.inline("✅ МОЁ", f"keep_{phone}")
                            ]]
                        )
            except Exception as e:
                print(f'Ошибка проверки: {e}')
        
        return True
    except Exception as e:
        print(f'❌ {phone}: {e}')
        return False
    finally:
        connecting.discard(phone)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'accounts': len(clients)}), 200

@app.route('/accounts', methods=['GET'])
def get_accounts():
    c.execute('SELECT phone FROM accounts')
    accs = c.fetchall()
    accounts = []
    for phone in accs:
        status = 'online' if phone[0] in clients else 'offline'
        accounts.append({'phone': phone[0], 'status': status})
    return jsonify(accounts), 200

@app.route('/accounts', methods=['POST'])
def add_account():
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone or not phone.startswith('+'):
        return jsonify({'error': 'Invalid phone format'}), 400
    
    try:
        session = phone.replace('+', '')
        c.execute('INSERT OR REPLACE INTO accounts VALUES (?, ?)', (phone, session))
        conn.commit()
        
        # Start account in background
        asyncio.create_task(start_account(phone, session))
        
        return jsonify({'status': 'added', 'phone': phone}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/accounts/<phone>', methods=['DELETE'])
def delete_account(phone):
    try:
        c.execute('DELETE FROM accounts WHERE phone = ?', (phone,))
        conn.commit()
        if phone in clients:
            asyncio.create_task(clients[phone].disconnect())
            del clients[phone]
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

async def init_bot():
    """Initialize Telegram bot"""
    global bot
    try:
        bot = TelegramClient('bot', API_ID, API_HASH)
        await bot.start(bot_token=BOT_TOKEN)
        print('🤖 БОТ ИНИЦИАЛИЗИРОВАН')
    except Exception as e:
        print(f'❌ Ошибка инициализации бота: {e}')
        return
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_cmd(event):
        if not is_admin(event.sender_id):
            return await event.reply('⛔ НЕТ ДОСТУПА')
        await event.reply('🤖 БОТ ГОТОВ', buttons=[
            [Button.inline('📋 СПИСОК', 'list')],
            [Button.inline('🔄 РЕСТАРТ', 'restart')]
        ])

    @bot.on(events.CallbackQuery(data='list'))
    async def list_acc(event):
        if not is_admin(event.sender_id):
            return await event.answer('НЕТ ДОСТУПА', alert=True)
        
        c.execute('SELECT phone FROM accounts')
        accs = c.fetchall()
        if not accs:
            return await event.edit('📭 ПУСТО')
        
        msg = '📋 АККАУНТЫ:\n\n'
        for phone in accs:
            status = '🟢' if phone[0] in clients else '🔴'
            msg += f'{status} {phone[0]}\n'
        await event.edit(msg)

    @bot.on(events.CallbackQuery(data='restart'))
    async def restart_acc(event):
        if not is_admin(event.sender_id):
            return await event.answer('НЕТ ДОСТУПА', alert=True)
        
        await event.edit('🔄 ПЕРЕЗАПУСК...')
        for phone, client in list(clients.items()):
            try:
                await client.disconnect()
            except:
                pass
        clients.clear()
        
        c.execute('SELECT phone, session_name FROM accounts')
        for idx, (phone, session) in enumerate(c.fetchall()):
            # Add delay between reconnections to avoid flood
            await asyncio.sleep(2 + idx * 1)
            await start_account(phone, session)
        
        await event.edit('✅ ПЕРЕЗАПУЩЕНО')

    @bot.on(events.CallbackQuery(data=lambda x: x and x.startswith('kick_')))
    async def kick(event):
        try:
            parts = event.data.decode().split('_')
            if len(parts) >= 3:
                phone = parts[1]
                hash_str = parts[2]
                if phone in clients:
                    auths = await clients[phone](GetAuthorizationsRequest())
                    for auth in auths.authorizations:
                        if str(auth.hash) == hash_str:
                            await clients[phone](ResetAuthorizationRequest(hash=int(hash_str)))
                            await event.edit('✅ СЕССИЯ КИНУТА')
                            break
        except Exception as e:
            print(f'Кик ошибка: {e}')

    @bot.on(events.CallbackQuery(data=lambda x: x and x.startswith('keep_')))
    async def keep(event):
        await event.edit('✅ ОСТАВЛЕНО')

async def run_bot():
    """Main bot loop"""
    await init_bot()
    
    # Load and start all accounts with delays
    c.execute('SELECT phone, session_name FROM accounts')
    accounts = c.fetchall()
    
    for idx, (phone, session) in enumerate(accounts):
        # Add delay between account starts to prevent flooding
        await asyncio.sleep(3 + idx * 2)
        try:
            await start_account(phone, session)
        except Exception as e:
            print(f'Error starting {phone}: {e}')
    
    print('🚀 ВСЕ АККАУНТЫ ЗАГРУЖЕНЫ')
    
    # Keep bot running
    if bot:
        await bot.run_until_disconnected()

def start_bot_thread():
    """Start bot in separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot())
    except Exception as e:
        print(f'Bot error: {e}')
    finally:
        loop.close()

if __name__ == '__main__':
    # Start bot in background thread
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()
    
    # Small delay to let bot start
    time.sleep(2)
    
    # Start Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
