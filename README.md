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

## 📦 Быстрый старт на Railway

### 1️⃣ Форкни репозиторий
https://github.com/sahrukhanveliev21-debug/shron

### 2️⃣ Создай Railway проект
- Перейди на https://railway.app
- Нажми "New Project"
- Выбери "Deploy from GitHub"
- Выбери свой форк репозитория

### 3️⃣ Добавь Environment Variables
В Railway Dashboard → Settings → Variables:

```env
API_ID=2040
API_HASH=b18441a1ff607e10a989891a5462e627
BOT_TOKEN=8351363618:AAHmq7zZSZSeLaylwKjfGzgku1DUlVZuekE
ADMIN_IDS=5454585281
```

**Как получить эти данные:**
- `API_ID` и `API_HASH` → https://my.telegram.org/apps
- `BOT_TOKEN` → напиши BotFather в Telegram: `/newbot`
- `ADMIN_IDS` → напиши @userinfobot в Telegram чтобы узнать свой ID

### 4️⃣ Деплой готов! 🚀
Railway автоматически задеплоит приложение

## 📡 API Endpoints

### 1. Проверка статуса
```bash
curl https://your-railway-url/health
```

**Ответ:**
```json
{
  "status": "ok",
  "accounts": 5
}
```

### 2. Получить все аккаунты
```bash
curl https://your-railway-url/accounts
```

**Ответ:**
```json
[
  {"phone": "+79991234567", "status": "online"},
  {"phone": "+79999876543", "status": "offline"}
]
```

### 3. Добавить аккаунт
```bash
curl -X POST https://your-railway-url/accounts \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79991234567"}'
```

**Ответ:**
```json
{
  "status": "added",
  "phone": "+79991234567"
}
```

### 4. Удалить аккаунт
```bash
curl -X DELETE https://your-railway-url/accounts/%2B79991234567
```

**Ответ:**
```json
{
  "status": "deleted"
}
```

## 🤖 Команды бота в Telegram

**Команды:**
- `/start` - главное меню

**Кнопки:**
- 📋 **СПИСОК** - показать все аккаунты и их статус
- 🔄 **РЕСТАРТ** - перезапустить все сессии

**При новом входе:**
- 🚫 **КИНУТЬ** - заблокировать сессию
- ✅ **МОЁ** - одобрить сессию

## 📊 Как это работает

1. **Добавление аккаунта** - через API или бота
2. **Подключение** - бот подключается к Telegram с задержками (без флуда)
3. **Мониторинг** - следит за новыми входами 24/7
4. **Оповещение** - отправляет тебе данные о новом входе
5. **Действие** - ты кикаешь или оставляешь сессию

## 💾 Хранение данных

- `accounts.db` (SQLite) - локальное хранилище на Railway
- `sessions/` - папка с сессиями Telethon

⚠️ **Важно:** При перезагрузке Railway данные теряются!

**Для постоянного хранения:**
- Используй PostgreSQL в Railway (бесплатный тарифф)
- Или подключи GitHub для синхронизации

## 🔧 Локальное тестирование

```bash
# Клонируй репо
git clone https://github.com/sahrukhanveliev21-debug/shron.git
cd shron

# Установи зависимости
pip install -r requirements.txt

# Создай .env файл
cp .env.example .env
# Отредактируй .env с твоими данными

# Запусти
python main.py
```

Приложение будет доступно на http://localhost:5000

## 🐛 Troubleshooting

### Бот не отвечает
1. Проверь логи в Railway Dashboard
2. Убедись что `BOT_TOKEN` правильный
3. Перезагрузи приложение: Railway → Settings → Restart

### Аккаунты не подключаются
1. Проверь `API_ID` и `API_HASH`
2. Убедись что номер в формате `+79991234567`
3. Проверь FloodWait ошибки в логах (нормально - Railway добавит задержки)

### Аккаунт требует 2FA код
1. Аккаунт нужно добавить локально сначала с кодом
2. Потом сессия сохранится и будет работать на Railway

## 📝 Тестирование credentials

```bash
python test_credentials.py
```

Проверит правильность `API_ID`, `API_HASH` и `BOT_TOKEN`

## 🔐 Безопасность

- Только администраторы (`ADMIN_IDS`) имеют доступ
- Сессии шифруются Telethon
- Environment variables защищены Railway
- Не коммитти `.env` файл с реальными данными!

## 📊 Примеры использования

### Python
```python
import requests

url = "https://your-railway-url"

# Получить аккаунты
accounts = requests.get(f"{url}/accounts").json()

# Добавить аккаунт
response = requests.post(
    f"{url}/accounts",
    json={"phone": "+79991234567"}
)

# Удалить аккаунт
requests.delete(f"{url}/accounts/%2B79991234567")
```

### JavaScript/Node.js
```javascript
const url = "https://your-railway-url";

// Получить аккаунты
const accounts = await fetch(`${url}/accounts`).then(r => r.json());

// Добавить аккаунт
await fetch(`${url}/accounts`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ phone: "+79991234567" })
});
```

## 📝 Лицензия

MIT

## 🚀 Готово!

Твой бот теперь работает 24/7 на Railway! 🎉

**Следующие шаги:**
1. Добавь первый аккаунт через API или бота
2. Следи за уведомлениями в Telegram
3. Кикай подозрительные входы
4. Enjoy! 😎
