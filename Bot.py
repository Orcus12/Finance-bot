import os
import logging
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

# Состояния
CATEGORY, AMOUNT, DESCRIPTION = range(3)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💰 Доход", "💸 Расход"],
        ["📊 Анализ месяца", "📋 История"],
        ["💡 Инвест-совет", "ℹ️ Помощь"]
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
💡 *Инвест-совет* - куда инвестировать
ℹ️ *Помощь* - эта справка
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
    elif text == "ℹ️ Помощь":
        return await help_command(update, context)

def main():
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    if not TOKEN:
        logging.error("❌ TELEGRAM_TOKEN не установлен!")
        return
    
    # Создаем Application (современный способ)
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
    logging.info("✅ Бот запущен с Application!")
    application.run_polling()

if __name__ == '__main__':
    main()
