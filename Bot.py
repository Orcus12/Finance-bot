import os
import logging
import requests
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ====== НАСТРОЙКИ ======
TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Хранение данных в памяти
user_finances = {}

# Категории
INCOME_CATS = ["💰 Зарплата", "💻 Фриланс", "📈 Инвестиции", "🎁 Прочее"]
EXPENSE_CATS = ["🍕 Еда", "🚗 Транспорт", "🏠 Жилье", "🎮 Развлечения", "🏥 Здоровье", "👕 Одежда", "📱 Прочее"]

# Инвестиционные возможности
INVESTMENT_OPPORTUNITIES = {
    "🚀 Высокий риск": [
        "📈 Акции роста (Tesla, Nvidia)",
        "🪙 Крипта (BTC, ETH, SOL)",
        "🔬 Биотех акции",
        "🤖 AI компании"
    ],
    "⚡ Средний риск": [
        "📊 ETF на tech-сектор",
        "🌎 Акции развивающихся рынков",
        "🔋 Green energy компании",
        "💻 Кибербезопасность"
    ],
    "🛡️ Консервативный": [
        "🏦 Облигации корпоративные",
        "📈 Дивидендные акции",
        "🪙 Стейблкоины (до 12% годовых)",
        "💰 P2P кредитование"
    ]
}

# Состояния
CATEGORY, AMOUNT, DESCRIPTION = range(3)

# ====== ФУНКЦИИ ДЛЯ КУРСОВ ВАЛЮТ ======
def get_currency_rates():
    """Получает актуальные курсы валют"""
    try:
        # ЦБ РФ API
        response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js', timeout=5)
        data = response.json()
        
        usd_rate = data['Valute']['USD']['Value']
        eur_rate = data['Valute']['EUR']['Value']
        usd_change = data['Valute']['USD']['Value'] - data['Valute']['USD']['Previous']
        eur_change = data['Valute']['EUR']['Value'] - data['Valute']['EUR']['Previous']
        
        return {
            'USD': {'rate': usd_rate, 'change': usd_change},
            'EUR': {'rate': eur_rate, 'change': eur_change},
            'timestamp': datetime.now().strftime("%H:%M")
        }
    except:
        # Fallback данные
        return {
            'USD': {'rate': 95.5, 'change': 0.3},
            'EUR': {'rate': 102.1, 'change': -0.2},
            'timestamp': 'кэш'
        }

def get_crypto_rates():
    """Получает курсы крипты"""
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true', timeout=5)
        data = response.json()
        
        return {
            'BTC': {
                'price': data['bitcoin']['usd'],
                'change': data['bitcoin']['usd_24h_change']
            },
            'ETH': {
                'price': data['ethereum']['usd'], 
                'change': data['ethereum']['usd_24h_change']
            },
            'SOL': {
                'price': data['solana']['usd'],
                'change': data['solana']['usd_24h_change']
            }
        }
    except:
        return {
            'BTC': {'price': 45000, 'change': 2.1},
            'ETH': {'price': 2500, 'change': 1.5},
            'SOL': {'price': 120, 'change': -0.5}
        }

def get_currency_advice(currency_data):
    """Дает совет по валютам"""
    usd_trend = "растет" if currency_data['USD']['change'] > 0 else "падает"
    eur_trend = "растет" if currency_data['EUR']['change'] > 0 else "падает"
    
    if currency_data['USD']['change'] > 0.5 and currency_data['EUR']['change'] > 0.5:
        return "💵 Доллар и евро растут - хорошее время для покупки валюты"
    elif currency_data['USD']['change'] < -0.5 and currency_data['EUR']['change'] < -0.5:
        return "🔄 Валюты падают - можно подождать с покупкой"
    elif usd_trend != eur_trend:
        return "📊 Разные тренды - диверсифицируйте валютную корзину"
    else:
        return "⚖️ Рынок стабилен - придерживайтесь стратегии"

# ====== БАЗОВЫЕ ФУНКЦИИ ======
def init_user(user_id):
    if user_id not in user_finances:
        user_finances[user_id] = {'transactions': []}

def add_transaction(user_id, trans_type, category, amount, description=""):
    init_user(user_id)
    transaction = {
        'date': datetime.now(),
        'type': trans_type,
        'category': category,
        'amount': amount,
        'description': description
    }
    user_finances[user_id]['transactions'].append(transaction)
    return True

def get_monthly_analysis(user_id):
    init_user(user_id)
    current_month = datetime.now().month
    total_income = sum(t['amount'] for t in user_finances[user_id]['transactions'] 
                      if t['type'] == 'income' and t['date'].month == current_month)
    total_expenses = sum(t['amount'] for t in user_finances[user_id]['transactions'] 
                        if t['type'] == 'expense' and t['date'].month == current_month)
    free_money = total_income - total_expenses
    return total_income, total_expenses, free_money

def get_investment_advice(free_money):
    if free_money <= 0:
        return "❌ В этом месяце нет свободных средств. Рекомендую сократить расходы."
    elif free_money < 3000:
        return f"💡 Можно инвестировать {free_money:,.0f} руб. в консервативные инструменты."
    elif free_money < 10000:
        return f"👍 {free_money:,.0f} руб. - хорошая сумма. Рекомендую: 50% в облигации, 50% в ETF на акции."
    else:
        return f"🚀 Отлично! {free_money:,.0f} руб.: 60% акции, 30% облигации, 10% валюта."

def get_aggressive_advice(amount):
    """Советы для агрессивного роста"""
    if amount < 5000:
        return "Рассмотрите крипту малых капитализаций (высокий риск!)"
    elif amount < 20000:
        return "60% - крипта (BTC/ETH), 40% - AI акции"
    elif amount < 50000:
        return "50% - крипта, 30% - tech ETF, 20% - облигации"
    else:
        return "40% - крипта, 40% - акции роста, 20% - диверсификация"

# ====== КОМАНДЫ БОТА ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💰 Доход", "💸 Расход"],
        ["📊 Анализ месяца", "📋 История"],
        ["💡 Инвест-совет", "🚀 X2 Инвест"],
        ["💱 Курсы валют", "ℹ️ Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "💼 **Финансовый помощник**\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 **Доступные команды:**

💰 *Доход* - добавить доход
💸 *Расход* - добавить расход
📊 *Анализ месяца* - финансовый отчет
📋 *История* - последние операции
💡 *Инвест-совет* - базовые рекомендации
🚀 *X2 Инвест* - агрессивные стратегии
💱 *Курсы валют* - актуальные котировки
ℹ️ *Помощь* - эта справка
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ====== ДИАЛОГИ ДЛЯ ТРАНЗАКЦИЙ ======
async def start_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[cat] for cat in INCOME_CATS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите категорию дохода:", reply_markup=reply_markup)
    context.user_data['type'] = 'income'
    return CATEGORY

async def start_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[cat] for cat in EXPENSE_CATS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите категорию расхода:", reply_markup=reply_markup)
    context.user_data['type'] = 'expense'
    return CATEGORY

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text
    await update.message.reply_text("💵 Введите сумму:")
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(',', '.'))
        context.user_data['amount'] = amount
        await update.message.reply_text("📝 Введите описание (или 'пропустить'):")
        return DESCRIPTION
    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму:")
        return AMOUNT

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    if description.lower() != 'пропустить':
        context.user_data['description'] = description
    
    await save_transaction(update, context)
    return ConversationHandler.END

async def save_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_id = update.message.from_user.id
    
    success = add_transaction(
        user_id,
        user_data['type'],
        user_data['category'],
        user_data['amount'],
        user_data.get('description', '')
    )
    
    if success:
        emoji = "💰" if user_data['type'] == 'income' else "💸"
        type_ru = "Доход" if user_data['type'] == 'income' else "Расход"
        await update.message.reply_text(f"{emoji} {type_ru} {user_data['amount']:,.0f}₽ добавлен!")
    
    context.user_data.clear()
    await start(update, context)

# ====== АНАЛИЗ И ОТЧЕТЫ ======
async def show_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    income, expenses, free_money = get_monthly_analysis(user_id)
    advice = get_investment_advice(free_money)
    
    text = f"""
📊 **Анализ за месяц:**

💰 Доходы: {income:,.0f}₽
💸 Расходы: {expenses:,.0f}₽
💎 Свободно: {free_money:,.0f}₽

{advice}
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def show_recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    init_user(user_id)
    transactions = user_finances[user_id]['transactions'][-5:]
    
    if not transactions:
        await update.message.reply_text("📭 Нет операций")
        return
    
    text = "📋 Последние операции:\n"
    for trans in reversed(transactions):
        emoji = "💰" if trans['type'] == 'income' else "💸"
        text += f"{emoji} {trans['amount']:,.0f}₽ - {trans['category']}\n"
    
    await update.message.reply_text(text)

async def show_advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    income, expenses, free_money = get_monthly_analysis(user_id)
    
    text = f"""
💡 **Инвест-совет**

Свободные средства: {free_money:,.0f}₽

{get_investment_advice(free_money)}
"""
    await update.message.reply_text(text, parse_mode='Markdown')

# ====== НОВЫЕ ФИЧИ ======
async def quick_investment_advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Моментальный совет для 2x"""
    user_id = update.message.from_user.id
    income, expenses, free_money = get_monthly_analysis(user_id)
    
    if free_money <= 0:
        await update.message.reply_text("❌ Нет свободных средств для инвестиций")
        return
    
    # Анализ риска на основе суммы
    if free_money < 10000:
        risk_level = "🚀 Высокий риск"
        advice = "💡 Маленькая сумма - можно рискнуть на крипту или акции роста"
    elif free_money < 50000:
        risk_level = "⚡ Средний риск" 
        advice = "💪 Идеально для диверсификации - tech ETF + крипта"
    else:
        risk_level = "🛡️ Консервативный"
        advice = "🏦 Крупная сумма - лучше диверсифицировать"
    
    crypto_data = get_crypto_rates()
    
    text = f"""
🎯 **МОМЕНТАЛЬНЫЙ СОВЕТ ДЛЯ 2X**

Свободно: *{free_money:,.0f} ₽*
Уровень риска: *{risk_level}*

{advice}

📊 **ТОП СЕЙЧАС:**
• Bitcoin: ${crypto_data['BTC']['price']:,.0f} 
• Ethereum: ${crypto_data['ETH']['price']:,.0f}
• Solana: ${crypto_data['SOL']['price']:,.1f}

🚀 **Варианты для быстрого роста:**
"""
    
    # Добавляем варианты по уровню риска
    for option in INVESTMENT_OPPORTUNITIES[risk_level]:
        text += f"• {option}\n"
    
    text += f"\n💡 *Совет:* {get_aggressive_advice(free_money)}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def show_currency_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает актуальные курсы"""
    
    # Получаем данные
    currency_data = get_currency_rates()
    crypto_data = get_crypto_rates()
    
    # Форматируем изменения
    def format_change(change):
        if change > 0:
            return f"📈 +{change:.2f}"
        elif change < 0:
            return f"📉 {change:.2f}"
        else:
            return "➡️ 0.00"
    
    text = f"""
💱 **АКТУАЛЬНЫЕ КУРСЫ** (обновлено {currency_data['timestamp']})

🇺🇸 **ДОЛЛАР (USD):**
   💵 {currency_data['USD']['rate']:.2f} ₽ {format_change(currency_data['USD']['change'])}

🇪🇺 **ЕВРО (EUR):**
   💶 {currency_data['EUR']['rate']:.2f} ₽ {format_change(currency_data['EUR']['change'])}

🪙 **КРИПТОВАЛЮТЫ:**
   ₿ Bitcoin: ${crypto_data['BTC']['price']:,.0f} {format_change(crypto_data['BTC']['change'])}%
   🔷 Ethereum: ${crypto_data['ETH']['price']:,.0f} {format_change(crypto_data['ETH']['change'])}%  
   🔶 Solana: ${crypto_data['SOL']['price']:,.1f} {format_change(crypto_data['SOL']['change'])}%

💡 **СОВЕТ:** {get_currency_advice(currency_data)}
"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ====== ОБРАБОТКА СООБЩЕНИЙ ======
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "💰 Доход":
        return await start_income(update, context)
    elif text == "💸 Расход":
        return await start_expense(update, context)
    elif text == "📊 Анализ месяца":
        return await show_analysis(update, context)
    elif text == "📋 История":
        return await show_recent(update, context)
    elif text == "💡 Инвест-совет":
        return await show_advice(update, context)
    elif text == "🚀 X2 Инвест":
        return await quick_investment_advice(update, context)
    elif text == "💱 Курсы валют":
        return await show_currency_rates(update, context)
    elif text == "ℹ️ Помощь":
        return await help_command(update, context)

# ====== ЗАПУСК БОТА ======
def main():
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    if not TOKEN:
        logging.error("❌ TELEGRAM_TOKEN не установлен!")
        return
    
    # Создаем Application
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analysis", show_analysis))
    application.add_handler(CommandHandler("recent", show_recent))
    application.add_handler(CommandHandler("advice", show_advice))
    
    # ConversationHandler для транзакций
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(💰 Доход|💸 Расход)$"), handle_text)
        ],
        states={
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)]
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)
    
    # Обработчик текста
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запускаем бота
    logging.info("✅ Бот запущен с новыми фичами!")
    application.run_polling()

if __name__ == '__main__':
    main()
