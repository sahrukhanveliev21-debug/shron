import asyncio
import sqlite3
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import SessionPasswordNeededError

API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = '8351363618:AAHmq7zZSZSeLaylwKjfGzgku1DUlVZuekE'
ADMIN_IDS = [5454585281]

os.makedirs('sessions', exist_ok=True)
conn = sqlite3.connect('accounts.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session_name TEXT)')
conn.commit()

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
        async def handler(event):
            auths = await client(GetAuthorizationsRequest())
            for auth in auths.authorizations:
                if not auth.current:
                    await bot.send_message(
                        ADMIN_IDS[0],
                        f'⚠️ Новая сессия!\n📞 {phone}\n📱 {auth.device_model}\n🌐 {auth.ip}',
                        buttons=[[
                            Button.inline("🚫 Кинуть", f"kick_{phone}_{auth.hash}"),
                            Button.inline("✅ Мое", f"keep_{phone}")
                        ]]
                    )
        return True
    except Exception as e:
        print(f'❌ {phone}: {e}')
        return False

@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    if not is_admin(event.sender_id):
        return await event.reply('⛔ Нет доступа')
    await event.reply('👋 Бот готов', buttons=[
        [Button.inline('➕ Добавить', 'add')],
        [Button.inline('📋 Список', 'list')],
        [Button.inline('❌ Удалить', 'del')]
    ])

@bot.on(events.CallbackQuery(data='add'))
async def add_acc(event):
    if not is_admin(event.sender_id):
        return await event.answer('⛔', alert=True)
    await event.edit('📲 Введи номер +79991234567')
    
    async with bot.conversation(event.sender_id) as conv:
        phone = (await conv.get_response()).text.strip()
        if not phone.startswith('+'):
            return await event.reply('❌ Неверный формат')
        
        session = phone.replace('+', '')
        client = TelegramClient(f'sessions/{session}', API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.send_code_request(phone)
            await event.reply('📲 Введи код:')
            code = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                await event.reply('🔐 Введи пароль 2FA:')
                password = (await conv.get_response()).text.strip()
                await client.sign_in(password=password)
            
            c.execute('INSERT OR REPLACE INTO accounts VALUES (?, ?)', (phone, session))
            conn.commit()
            await start_account(phone, session)
            await event.reply(f'✅ {phone} добавлен')
        except Exception as e:
            await event.reply(f'❌ {e}')
        finally:
            await client.disconnect()

@bot.on(events.CallbackQuery(data='list'))
async def list_acc(event):
    if not is_admin(event.sender_id):
        return await event.answer('⛔', alert=True)
    
    c.execute('SELECT phone FROM accounts')
    accs = c.fetchall()
    if not accs:
        return await event.edit('📭 Пусто')
    
    msg = '📋 Аккаунты:\n'
    for phone in accs:
        status = '🟢' if phone[0] in clients else '🔴'
        msg += f'{status} {phone[0]}\n'
    await event.edit(msg)

@bot.on(events.CallbackQuery(data='del'))
async def del_acc(event):
    if not is_admin(event.sender_id):
        return await event.answer('⛔', alert=True)
    
    c.execute('SELECT phone FROM accounts')
    accs = c.fetchall()
    if not accs:
        return await event.edit('📭 Пусто')
    
    buttons = [[Button.inline(p[0], f'del_{p[0]}')] for p in accs]
    buttons.append([Button.inline('❌ Отмена', 'cancel')])
    await event.edit('🗑 Выбери:', buttons=buttons)

@bot.on(events.CallbackQuery(data=lambda x: x.startswith('del_')))
async def confirm_del(event):
    phone = event.data.decode().replace('del_', '')
    c.execute('DELETE FROM accounts WHERE phone = ?', (phone,))
    conn.commit()
    if phone in clients:
        await clients[phone].disconnect()
        del clients[phone]
    await event.edit(f'✅ {phone} удален')

@bot.on(events.CallbackQuery(data='cancel'))
async def cancel(event):
    await event.edit('❌ Отменено')

@bot.on(events.CallbackQuery(data=lambda x: x.startswith('kick_')))
async def kick(event):
    _, phone, hash_str = event.data.decode().split('_')
    if phone in clients:
        auths = await clients[phone](GetAuthorizationsRequest())
        for auth in auths.authorizations:
            if auth.hash == int(hash_str):
                await clients[phone](ResetAuthorizationRequest(hash=int(hash_str)))
                await event.edit('✅ Сессия кинута')
                break

@bot.on(events.CallbackQuery(data=lambda x: x.startswith('keep_')))
async def keep(event):
    await event.edit('✅ Оставлено')

async def main():
    c.execute('SELECT phone, session_name FROM accounts')
    for phone, session in c.fetchall():
        await start_account(phone, session)
    print('🚀 Бот запущен')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
