import os
import asyncio
import logging
import random
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
client = None
is_trading = False
current_asset = "EURUSD_otc"
trade_amount = 1.0
expiration_time = 60

async def init_pocket_option():
    """Инициализация клиента Pocket Option"""
    global client
    try:
        ssid_raw = os.getenv("PO_SSID")
        if not ssid_raw:
            logger.error("PO_SSID не найден в переменных окружения")
            return False
        
        # Если пришла просто строка (без фигурных скобок), оборачиваем её в JSON автоматически
        if not ssid_raw.strip().startswith('{'):
            ssid_json = json.dumps({
                "session": ssid_raw.strip(),
                "isDemo": 1,
                "uid": 0,
                "platform": 1
            })
        else:
            ssid_json = ssid_raw
            
        client = PocketOptionAsync(ssid=ssid_json)
        balance = await client.balance()
        logger.info(f"Успешное подключение к Pocket Option. Баланс: ${balance}")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к Pocket Option: {e}")
        return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Привет! Я торговый бот для Pocket Option.\n\n"
        "Команды:\n"
        "/status - Проверить статус подключения\n"
        "/balance - Показать баланс\n"
        "/trade - Начать/остановить торговлю",
        reply_markup=get_main_keyboard()
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = "🟢 Торговля активна" if is_trading else "🔴 Торговля остановлена"
    await update.message.reply_text(f"Статус: {status_text}")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if client is None:
            await update.message.reply_text("❌ Клиент не инициализирован.")
            return
        balance = await client.balance()
        await update.message.reply_text(f"💰 Баланс: ${balance:.2f}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("▶️ Начать торговлю", callback_data="start_trade")],
        [InlineKeyboardButton("⏹️ Остановить торговлю", callback_data="stop_trade")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_trading
    query = update.callback_query
    await query.answer()
    
    if query.data == "status":
        status_text = "🟢 Торговля активна" if is_trading else "🔴 Торговля остановлена"
        await query.edit_message_text(f"Статус: {status_text}")
    elif query.data == "balance":
        try:
            balance = await client.balance()
            await query.edit_message_text(f"💰 Баланс: ${balance:.2f}")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
    elif query.data == "start_trade":
        if not is_trading:
            is_trading = True
            await query.edit_message_text("🟢 Торговля запущена!")
            asyncio.create_task(trading_loop())
        else:
            await query.edit_message_text("Торговля уже запущена.")
    elif query.data == "stop_trade":
        is_trading = False
        await query.edit_message_text("🔴 Торговля остановлена.")

async def trading_loop():
    global is_trading, current_asset, trade_amount, expiration_time
    while is_trading:
        try:
            direction = random.choice(["call", "put"])
            logger.info(f"Сделка: {current_asset}, {direction}, {trade_amount}, {expiration_time}с")
            trade_result = await client.buy(
                asset=current_asset, amount=trade_amount,
                direction=direction, expiration=expiration_time
            )
            logger.info(f"Сделка открыта: {trade_result}")
            await asyncio.sleep(expiration_time + 5)
        except Exception as e:
            logger.error(f"Ошибка в цикле: {e}")
            await asyncio.sleep(10)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if not loop.run_until_complete(init_pocket_option()):
        print("Не удалось подключиться к Pocket Option.")
        return
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN не найден.")
        return
    
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()