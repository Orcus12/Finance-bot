import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ['TELEGRAM_TOKEN']
user_data = {}

INCOME_CATS = ["💰 Зарплата", "💻 Фриланс", "📈 Инвестиции", "🎁 Прочее"]
EXPENSE_CATS = ["🍕 Еда", "🚗 Транспорт", "🏠 Жилье", "🎮 Развлечения", "🏥 Здоровье", "👕 Одежда", "📱 Прочее"]

def init_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'transactions': []}

def add_transaction(user_id, trans_type, category, amount, description=""):
    init_user(user_id)
    transaction = {
        'date': datetime.now(),
        'type': trans_type,
        'category': category,
        'amount': amount,
        'description': description
    }
    user_data[user_id]['transactions'].append(transaction)
    return True

def get_analysis(user_id):
    init_user(user_id)
    current_month = datetime.now().month
    total_income = sum(t['amount'] for t in user_data[user_id]['transactions'] 
                      if t['type'] == 'income' and t['date'].month == current_month)
    total_expenses = sum(t['amount'] for t in user_data[user_id]['transactions'] 
                        if t['type'] == 'expense' and t['date'].month == current_month)
    free_money = total_income - total_expenses
    return total_income, total_expenses, free_money

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["💰 Доход", "💸 Расход"], ["📊 Анализ", "📋 История"], ["💡 Совет", "ℹ️ Помощь"]]
    await update.message.reply_text(
        "💼 Финансовый помощник\nВыберите действие:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    
    if text == "💰 Доход":
        await update.message.reply_text("Введите сумму дохода:")
        context.user_data['awaiting'] = 'income'
    elif text == "💸 Расход":
        await update.message.reply_text("Введите сумму расхода:")
        context.user_data['awaiting'] = 'expense'
    elif text == "📊 Анализ":
        income, expenses, free = get_analysis(user_id)
        advice = f"💡 Инвестируйте {free:,.0f} руб." if free > 0 else "❌ Свободных средств нет"
        await update.message.reply_text(f"Доходы: {income:,.0f}₽\nРасходы: {expenses:,.0f}₽\nСвободно: {free:,.0f}₽\n\n{advice}")
    elif text in ["💡 Совет", "ℹ️ Помощь"]:
        await update.message.reply_text("Просто добавляйте доходы/расходы и получайте инвестиционные советы!")
    elif text == "📋 История":
        init_user(user_id)
        transactions = user_data[user_id]['transactions'][-5:]
        if transactions:
            text = "📋 Последние операции:\n" + "\n".join([
                f"{'💰' if t['type']=='income' else '💸'} {t['amount']:,.0f}₽ - {t['category']}" 
                for t in transactions
            ])
            await update.message.reply_text(text)
        else:
            await update.message.reply_text("📭 Операций пока нет")
    else:
        if 'awaiting' in context.user_data:
            try:
                amount = float(text.replace(',', '.'))
                trans_type = context.user_data['awaiting']
                category = INCOME_CATS[0] if trans_type == 'income' else EXPENSE_CATS[0]
                
                add_transaction(user_id, trans_type, category, amount)
                await update.message.reply_text(f"✅ {'Доход' if trans_type == 'income' else 'Расход'} {amount:,.0f}₽ добавлен!")
                del context.user_data['awaiting']
            except ValueError:
                await update.message.reply_text("❌ Введите число:")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Для Railway
    port = int(os.environ.get('PORT', 8000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"https://your-app-name.up.railway.app/{TOKEN}",
        secret_token='WEBHOOK_SECRET'
    )

if __name__ == '__main__':
    main()
