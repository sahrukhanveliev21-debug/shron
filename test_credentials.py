import os
import asyncio
from telethon import TelegramClient

API_ID = int(os.getenv('API_ID', '2040'))
API_HASH = os.getenv('API_HASH', 'b18441a1ff607e10a989891a5462e627')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8351363618:AAHmq7zZSZSeLaylwKjfGzgku1DUlVZuekE')

async def check_credentials():
    """Test bot credentials"""
    try:
        bot = TelegramClient('test_session', API_ID, API_HASH)
        await bot.start(bot_token=BOT_TOKEN)
        print('✅ Credentials OK')
        await bot.disconnect()
        return True
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(check_credentials())
    exit(0 if result else 1)
