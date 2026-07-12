import asyncio
import sqlite3
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

# ========== КОНФИГУРАЦИЯ ==========
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = '8351363618:AAHmq7zZSZSeLaylwKjfGzgku1DUlVZuekE'
ADMIN_IDS = [5454585281]

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        os.makedirs('sessions', exist_ok=True)
        self.conn = sqlite3.connect('accounts.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                phone TEXT PRIMARY KEY,
                session_name TEXT,
                added_at TEXT
            )
        ''')
        self.conn.commit()

    def add_account(self, phone, session_name):
        self.cursor.execute(
            'INSERT OR REPLACE INTO accounts VALUES (?, ?, ?)',
            (phone, session_name, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_accounts(self):
        self.cursor.execute('SELECT phone, session_name FROM accounts')
        return self.cursor.fetchall()

    def delete_account(self, phone):
        self.cursor.execute('DELETE FROM accounts WHERE phone = ?', (phone,))
        self.conn.commit()

db = Database()

# ========== ОСНОВНОЙ БОТ ==========
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
clients = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start_account(phone, session_name):
    try:
        client = TelegramClient(f'sessions/{session_name}', API_ID, API_HASH)
        await client.start(phone=phone)
        clients[phone] = client
        print(f'✅ Аккаунт {phone} запущен')
        
        @client.on(events.Album)
        @client.on(events.NewMessage)
        @client.on(events.MessageEdited)
        async def check_sessions(event):
            await check_new_sessions(phone, client)
        
        await check_new_sessions(phone, client)
        return True
    except Exception as e:
        print(f'❌ Ошибка запуска {phone}: {e}')
        return False

async def check_new_sessions(phone, client):
    try:
        auths = await client(GetAuthorizationsRequest())
        
        for auth in auths.authorizations:
            if not auth.current:
                device = auth.device_model or 'Неизвестно'
                platform = auth.platform or 'Неизвестно'
                ip = auth.ip or 'Неизвестно'
                country = auth.country or 'Неизвестно'
                date = datetime.fromtimestamp(auth.date_created).strftime('%d.%m.%Y %H:%M')
                
                msg = f"""
⚠️ **НОВАЯ СЕССИЯ!**

📞 `{phone}`
🕐 {date}

**Устройство:** {device}
**Платформа:** {platform}
**IP:** {ip}
**Страна:** {country}
**Hash:** `{auth.hash}`

Выберите действие:
"""
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            msg,
                            buttons=[
                                [
                                    Button.inline(f"🚫 Кинуть {device[:10]}", f"kick_{phone}_{auth.hash}"),
                                    Button.inline("✅ Это мое", f"keep_{phone}")
                                ]
                            ]
                        )
                    except:
                        pass
    except Exception as e:
        print(f'Ошибка проверки сессий для {phone}: {e}')

async def add_account_process(event, phone):
    session_name = phone.replace('+', '')
    client = TelegramClient(f'sessions/{session_name}', API_ID, API_HASH)
    await client.connect()
    
    try:
        await client.send_code_request(phone)
        await event.reply(f'📲 Код отправлен на {phone}\nВведи код (или "отмена" для отмены):')
        
        async with bot.conversation(event.sender_id) as conv:
            response = await conv.get_response()
            if response.text.lower() == 'отмена':
                await event.reply('❌ Добавление отменено')
                return
            
            code = response.text.strip()
            
            try:
                await client.sign_in(phone, code)
            except PhoneCodeInvalidError:
                await event.reply('❌ Неверный код! Попробуй снова /add')
                return
            except PhoneCodeExpiredError:
                await event.reply('❌ Код истек! Попробуй снова /add')
                return
            except SessionPasswordNeededError:
                await event.reply('🔐 **Требуется пароль двухфакторной аутентификации!**\n\nВведи пароль (или "отмена" для отмены):')
                
                password_response = await conv.get_response()
                if password_response.text.lower() == 'отмена':
                    await event.reply('❌ Добавление отменено')
                    return
                
                password = password_response.text.strip()
                
                try:
                    await client.sign_in(password=password)
                except Exception as e:
                    await event.reply(f'❌ Неверный пароль! Ошибка: {str(e)}')
                    return
            
            db.add_account(phone, session_name)
            await start_account(phone, session_name)
            await event.reply(f'✅ Аккаунт {phone} успешно добавлен!')
            
    except Exception as e:
        await event.reply(f'❌ Ошибка: {str(e)}')
    finally:
        await client.disconnect()

# ========== ОБРАБОТЧИКИ БОТА ==========

@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    if not is_admin(event.sender_id):
        await event.reply('⛔ У тебя нет доступа к этому боту!')
        return
    
    keyboard = [
        [Button.inline('➕ Добавить аккаунт', 'add_acc')],
        [Button.inline('📋 Список аккаунтов', 'list_acc')],
        [Button.inline('❌ Удалить аккаунт', 'del_acc')],
        [Button.inline('🔄 Перезапустить все', 'restart_all')]
    ]
    await event.reply('🤖 **Панель управления сессиями**\n\nВыбери действие:', buttons=keyboard)

@bot.on(events.CallbackQuery(data='add_acc'))
async def add_account_callback(event):
    if not is_admin(event.sender_id):
        await event.answer('⛔ Нет доступа!', alert=True)
        return
    
    await event.edit('📲 Введи номер телефона в формате:\n`+79991234567`\n\nИли напиши "отмена" для отмены.')
    
    async with bot.conversation(event.sender_id) as conv:
        response = await conv.get_response()
        phone = response.text.strip()
        
        if phone.lower() == 'отмена':
            await event.reply('❌ Добавление отменено')
            return
        
        if not phone.startswith('+'):
            await event.reply('❌ Неверный формат! Используй +79991234567')
            return
        
        await add_account_process(event, phone)

@bot.on(events.CallbackQuery(data='list_acc'))
async def list_accounts_callback(event):
    if not is_admin(event.sender_id):
        await event.answer('⛔ Нет доступа!', alert=True)
        return
    
    accounts = db.get_accounts()
    if not accounts:
        await event.edit('📭 Нет добавленных аккаунтов')
        return
    
    msg = '📋 **Список аккаунтов:**\n\n'
    for phone, _ in accounts:
        status = '🟢' if phone in clients else '🔴'
        msg += f'{status} `{phone}`\n'
    
    await event.edit(msg)

@bot.on(events.CallbackQuery(data='del_acc'))
async def delete_account_callback(event):
    if not is_admin(event.sender_id):
        await event.answer('⛔ Нет доступа!', alert=True)
        return
    
    accounts = db.get_accounts()
    if not accounts:
        await event.edit('📭 Нет аккаунтов для удаления')
        return
    
    buttons = []
    for phone, _ in accounts:
        buttons.append([Button.inline(phone, f'confirm_del_{phone}')])
    buttons.append([Button.inline('❌ Отмена', 'cancel')])
    
    await event.edit('🗑 **Выбери аккаунт для удаления:**', buttons=buttons)

@bot.on(events.CallbackQuery(data=lambda x: x.startswith('confirm_del_')))
async def confirm_delete(event):
    if not is_admin(event.sender_id):
        await event.answer('⛔ Нет доступа!', alert=True)
        return
    
    phone = event.data.decode().replace('confirm_del_', '')
    db.delete_account(phone)
    
    if phone in clients:
        await clients[phone].disconnect()
        del clients[phone]
    
    await event.edit(f'✅ Аккаунт {phone} удален')

@bot.on(events.CallbackQuery(data='restart_all'))
async def restart_all(event):
    if not is_admin(event.sender_id):
        await event.answer('⛔ Нет доступа!', alert=True)
        return
    
    await event.edit('🔄 Перезапускаю все аккаунты...')
    
    for phone, client in clients.items():
        try:
            await client.disconnect()
        except:
            pass
    clients.clear()
    
    accounts = db.get_accounts()
    for phone, session_name in accounts:
        await start_account(phone, session_name)
    
    await event.edit(f'✅ Перезапущено {len(accounts)} аккаунтов')

@bot.on(events.CallbackQuery(data=lambda x: x.startswith('kick_') or x.startswith('keep_')))
async def handle_session_buttons(event):
    if not is_admin(event.sender_id):
        await event.answer('⛔ Нет доступа!', alert=True)
        return
    
    data = event.data.decode()
    
    if data.startswith('kick_'):
        _, phone, hash_str = data.split('_')
        if phone in clients:
            try:
                auths = await clients[phone](GetAuthorizationsRequest())
                for auth in auths.authorizations:
                    if auth.hash == int(hash_str):
                        await clients[phone](ResetAuthorizationRequest(hash=int(hash_str)))
                        await event.edit('✅ Сессия успешно завершена!')
                        break
            except Exception as e:
                await event.edit(f'❌ Ошибка: {str(e)}')
    
    elif data.startswith('keep_'):
        _, phone = data.split('_')
        await event.edit('✅ Сессия оставлена')

@bot.on(events.CallbackQuery(data='cancel'))
async def cancel_callback(event):
    await event.edit('❌ Действие отменено')

# ========== ЗАПУСК ==========
async def main():
    print('🚀 Запуск бота...')
    
    accounts = db.get_accounts()
    for phone, session_name in accounts:
        await start_account(phone, session_name)
    
    print(f'✅ Запущено {len(clients)} аккаунтов')
    print('🤖 Бот готов к работе!')
    
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
