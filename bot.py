import asyncio
import sqlite3
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import time

# ===== КОНФИГ =====
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = '8351363618:AAHmq7zZSZSeLaylwKjfGzgku1DUlVZuekE'
ADMIN_IDS = [5454585281]

# ===== БАЗА =====
os.makedirs('sessions', exist_ok=True)
conn = sqlite3.connect('accounts.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session_name TEXT)')
conn.commit()

# ===== БОТ =====
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
clients = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start_account(phone, session_name):
    try:
        client = TelegramClient(f'sessions/{session_name}', API_ID, API_HASH)
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
                print(f'Ошибка: {e}')
        return True
    except FloodWaitError as e:
        print(f'⏳ Флуд-вейт {e.seconds} секунд для {phone}')
        await asyncio.sleep(e.seconds)
        return await start_account(phone, session_name)
    except Exception as e:
        print(f'❌ {phone}: {e}')
        return False

@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    if not is_admin(event.sender_id):
        return await event.reply('⛔ НЕТ ДОСТУПА')
    await event.reply('🤖 БОТ ГОТОВ', buttons=[
        [Button.inline('➕ ДОБАВИТЬ', 'add')],
        [Button.inline('📋 СПИСОК', 'list')],
        [Button.inline('❌ УДАЛИТЬ', 'del')],
        [Button.inline('🔄 РЕСТАРТ', 'restart')]
    ])

@bot.on(events.CallbackQuery(data='add'))
async def add_acc(event):
    if not is_admin(event.sender_id):
        return await event.answer('НЕТ ДОСТУПА', alert=True)
    
    await event.edit('📲 ВВЕДИ НОМЕР:\n+79991234567')
    
    async with bot.conversation(event.sender_id) as conv:
        phone = (await conv.get_response()).text.strip()
        if not phone.startswith('+'):
            return await event.reply('❌ НЕВЕРНЫЙ ФОРМАТ')
        
        session = phone.replace('+', '')
        client = TelegramClient(f'sessions/{session}', API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.send_code_request(phone)
            await event.reply('📲 ВВЕДИ КОД:')
            code = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                await event.reply('🔐 ВВЕДИ ПАРОЛЬ 2FA:')
                pwd = (await conv.get_response()).text.strip()
                await client.sign_in(password=pwd)
            except FloodWaitError as e:
                await event.reply(f'⏳ ЖДИ {e.seconds} СЕКУНД')
                return
            
            c.execute('INSERT OR REPLACE INTO accounts VALUES (?, ?)', (phone, session))
            conn.commit()
            await start_account(phone, session)
            await event.reply(f'✅ {phone} ДОБАВЛЕН')
        except Exception as e:
            await event.reply(f'❌ {str(e)[:100]}')
        finally:
            await client.disconnect()

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

@bot.on(events.CallbackQuery(data='del'))
async def del_acc(event):
    if not is_admin(event.sender_id):
        return await event.answer('НЕТ ДОСТУПА', alert=True)
    
    c.execute('SELECT phone FROM accounts')
    accs = c.fetchall()
    if not accs:
        return await event.edit('📭 ПУСТО')
    
    buttons = [[Button.inline(p[0], f'del_{p[0]}')] for p in accs]
    buttons.append([Button.inline('❌ ОТМЕНА', 'cancel')])
    await event.edit('🗑 ВЫБЕРИ:', buttons=buttons)

@bot.on(events.CallbackQuery(data='restart'))
async def restart_acc(event):
    if not is_admin(event.sender_id):
        return await event.answer('НЕТ ДОСТУПА', alert=True)
    
    await event.edit('🔄 ПЕРЕЗАПУСК...')
    for phone, client in clients.items():
        try:
            await client.disconnect()
        except:
            pass
    clients.clear()
    
    c.execute('SELECT phone, session_name FROM accounts')
    for phone, session in c.fetchall():
        await start_account(phone, session)
    
    await event.edit('✅ ПЕРЕЗАПУЩЕНО')

@bot.on(events.CallbackQuery(data=lambda x: x and x.startswith('del_')))
async def confirm_del(event):
    phone = event.data.decode().replace('del_', '')
    c.execute('DELETE FROM accounts WHERE phone = ?', (phone,))
    conn.commit()
    if phone in clients:
        await clients[phone].disconnect()
        del clients[phone]
    await event.edit(f'✅ {phone} УДАЛЕН')

@bot.on(events.CallbackQuery(data='cancel'))
async def cancel(event):
    await event.edit('❌ ОТМЕНЕНО')

@bot.on(events.CallbackQuery(data=lambda x: x and x.startswith('kick_')))
async def kick(event):
    try:
        _, phone, hash_str = event.data.decode().split('_')
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

async def main():
    print('🚀 ЗАПУСК БОТА...')
    c.execute('SELECT phone, session_name FROM accounts')
    for phone, session in c.fetchall():
        await start_account(phone, session)
    print('🤖 БОТ ГОТОВ')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
