import asyncio
import sqlite3
import os
import logging
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import SessionPasswordNeededError, RPCError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info(f'✅ {phone} запущен')
        
        @client.on(events.NewMessage)
        async def handler(event):
            try:
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
            except Exception as e:
                logger.error(f'Ошибка в handler {phone}: {e}')
        return True
    except Exception as e:
        logger.error(f'❌ {phone}: {e}')
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
    
    try:
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
    except Exception as e:
        logger.error(f'Ошибка добавления: {e}')

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

@bot.on(events.CallbackQuery(data=lambda x: x and x.startswith('del_')))
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

@bot.on(events.CallbackQuery(data=lambda x: x and x.startswith('kick_')))
async def kick(event):
    try:
        _, phone, hash_str = event.data.decode().split('_')
        if phone in clients:
            auths = await clients[phone](GetAuthorizationsRequest())
            for auth in auths.authorizations:
                if auth.hash == int(hash_str):
                    await clients[phone](ResetAuthorizationRequest(hash=int(hash_str)))
                    await event.edit('✅ Сессия кинута')
                    break
    except Exception as e:
        logger.error(f'Ошибка кика: {e}')

@bot.on(events.CallbackQuery(data=lambda x: x and x.startswith('keep_')))
async def keep(event):
    await event.edit('✅ Оставлено')

async def main():
    try:
        c.execute('SELECT phone, session_name FROM accounts')
        accounts = c.fetchall()
        for phone, session in accounts:
            await start_account(phone, session)
        logger.info(f'🚀 Бот запущен, аккаунтов: {len(accounts)}')
        await bot.run_until_disconnected()
    except Exception as e:
        logger.error(f'Критическая ошибка: {e}')
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Бот остановлен')
    except Exception as e:
        logger.error(f'Ошибка: {e}')
