# 🤖 Telegram Account Manager (Railway Edition)

Telegram бот для управления несколькими аккаунтами одновременно, развернутый на Railway. Отслеживает новые сессии на твоих аккаунтах и позволяет их блокировать или одобрять.

## 🎯 Возможности

- ✅ Работает 24/7 на облаке Railway
- ➕ **Добавление аккаунтов** - добавляй до 16+ аккаунтов через API
- 📋 **Список аккаунтов** - смотри статус каждого (онлайн/офлайн)
- ❌ **Удаление аккаунтов** - удаляй через API или бота
- 🔄 **Рестарт** - перезапускай все сессии через бота
- ⚠️ **Уведомления** - получай оповещения о новых входах в Telegram
- 🚫 **Блокировка сессий** - кикай подозрительные входы
- ✅ **Одобрение сессий** - оставляй свои входы

## 📦 Развертывание на Railway

### 1. Клонируй репозиторий
```bash
git clone https://github.com/sahrukhanveliev21-debug/shron.git
cd shron
```

### 2. Создай Railway проект
- Перейди на https://railway.app
- Нажми "New Project"
- Выбери "Deploy from GitHub"
- Выбери этот репозиторий

### 3. Добавь Environment Variables в Railway
В Railway Dashboard перейди в Variables и добавь:

```
API_ID=2040
API_HASH=b18441a1ff607e10a989891a5462e627
BOT_TOKEN=8351363618:AAHmq7zZSZSeLaylwKjfGzgku1DUlVZuekE
ADMIN_IDS=5454585281
PORT=5000
```

**Где взять эти данные:**
- `API_ID` и `API_HASH` - отсюда: https://my.telegram.org/apps
- `BOT_TOKEN` - от BotFather в Telegram
- `ADMIN_IDS` - твой Telegram ID (можно получить от @userinfobot)

### 4. Деплой
Railway автоматически задеплоит приложение! 🚀

## 📡 API Endpoints

### Health Check
```bash
GET https://your-railway-url/health
```
Ответ:
```json
{
  "status": "ok",
  "accounts": 5
}
```

### Получить все аккаунты
```bash
GET https://your-railway-url/accounts
```
Ответ:
```json
[
  {"phone": "+79991234567", "status": "online"},
  {"phone": "+79999876543", "status": "offline"}
]
```

### Добавить аккаунт
```bash
POST https://your-railway-url/accounts
Content-Type: application/json

{
  "phone": "+79991234567"
}
```

### Удалить аккаунт
```bash
DELETE https://your-railway-url/accounts/%2B79991234567
```

## 🤖 Команды в Telegram

- `/start` - главное меню

## 🎮 Кнопки

| Кнопка | Описание |
|--------|----------|
| 📋 СПИСОК | Показать все добавленные аккаунты и их статус |
| 🔄 РЕСТАРТ | Перезапустить все сессии |

## 📊 Как это работает

1. **Добавление аккаунта**: Через API или бота добавляешь номер
2. **Мониторинг**: Бот следит за новыми входами на каждый аккаунт 24/7
3. **Оповещение**: При новом входе бот отправляет инфо в Telegram (устройство, IP, страна, время)
4. **Действие**: Ты выбираешь в Telegram - кикать или оставить сессию

## 💾 База данных

- Все аккаунты хранятся в `accounts.db` (SQLite)
- Сессии сохраняются в папке `sessions/`
- На Railway используется локальное хранилище (теряется при перезагрузке)

⚠️ **Для постоянного хранения данных используй PostgreSQL на Railway!**

## 🔐 Безопасность

- Только администраторы (ADMIN_IDS) имеют доступ к командам
- Сессии шифруются Telethon
- Environment variables защищены Railway

## 🐛 Troubleshooting

### Бот не отвечает
- Проверь логи в Railway Dashboard
- Убедись что `BOT_TOKEN` правильный
- Перезагрузи приложение в Railway

### Аккаунты не работают
- Проверь `API_ID` и `API_HASH`
- Убедись что номер телефона в правильном формате (+79991234567)
- Проверь логи для подробных ошибок

## 📝 Локальное тестирование

```bash
pip install -r requirements.txt
python main.py
```

Приложение будет доступно на http://localhost:5000

## 📝 Лицензия

MIT

## 🚀 Готово!

Теперь твой бот работает 24/7 на Railway! 🎉
