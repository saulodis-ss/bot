import asyncio
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync

# ==========================================================
# ВСТАВЬТЕ ВАШИ ДАННЫЕ СЮДА:
# ==========================================================
TELEGRAM_BOT_TOKEN = "8891405691:AAH7QGErOKV5D1tLQWWi7yZDGpxVdFg15JI"
PO_SSID = "lu5leQuph5NhZwSbHnVHcqTxIQI9IWq8FfouuP6s-SV-f6Jvutw5-9OO6kEgJLQ9dcRGOrNpx3bseQ0bODkSq4En1NKk_oMPHvHII0wf4RE"
PO_UID = "0"
# ==========================================================

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
        if not PO_SSID or PO_SSID == "ВСТАВЬТЕ_СЮДА_ВАШ_SSID_ИЗ_POCKET_OPTION":
            logger.error("Вы не вставили SSID в код!")
            return False
        
        client = PocketOptionAsync(ssid=PO_SSID)
        # Проверяем подключение, получая баланс
        balance = await client.balance()
        logger.info(f"Успешное подключение к Pocket Option. Баланс: ${balance}")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к Pocket Option: {e}")
        return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 Привет! Я торговый бот для Pocket Option.\n\n"
        "Команды:\n"
        "/status - Проверить статус подключения\n"
        "/balance - Показать баланс\n"
        "/trade - Начать/остановить торговлю\n"
        "/settings - Настройки торговли",
        reply_markup=get_main_keyboard()
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка статуса бота"""
    status_text = "🟢 Торговля активна" if is_trading else "🔴 Торговля остановлена"
    await update.message.reply_text(f"Статус: {status_text}")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ баланса демо-счёта"""
    try:
        if client is None:
            await update.message.reply_text("❌ Клиент не инициализирован. Попробуйте позже.")
            return
        balance = await client.balance()
        await update.message.reply_text(f"💰 Баланс демо-счёта: ${balance:.2f}")
    except Exception as e:
        logger.error(f"Ошибка получения баланса: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = [
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("▶️ Начать торговлю", callback_data="start_trade")],
        [InlineKeyboardButton("⏹️ Остановить торговлю", callback_data="stop_trade")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    # ВАЖНО: Объявляем глобальную переменную в самом начале функции
    global is_trading
    
    query = update.callback_query
    await query.answer()
    
    if query.data == "status":
        status_text = "🟢 Торговля активна" if is_trading else "🔴 Торговля остановлена"
        await query.edit_message_text(f"Статус: {status_text}")
        
    elif query.data == "balance":
        try:
            balance = await client.balance()
            await query.edit_message_text(f"💰 Баланс демо-счёта: ${balance:.2f}")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
            
    elif query.data == "start_trade":
        if not is_trading:
            is_trading = True
            await query.edit_message_text("🟢 Торговля запущена!")
            # Запускаем торговый цикл в фоне
            asyncio.create_task(trading_loop())
        else:
            await query.edit_message_text("Торговля уже запущена.")
            
    elif query.data == "stop_trade":
        is_trading = False
        await query.edit_message_text("🔴 Торговля остановлена.")

async def trading_loop():
    """Основной цикл торговли"""
    global is_trading, current_asset, trade_amount, expiration_time
    
    logger.info("Запуск торгового цикла...")
    
    while is_trading:
        try:
            # Простая стратегия: случайный выбор направления (CALL/PUT)
            # В реальном боте здесь должна быть ваша стратегия анализа
            direction = random.choice(["call", "put"])
            
            logger.info(f"Открытие сделки: {current_asset}, {direction}, сумма: {trade_amount}, экспирация: {expiration_time}с")
            
            # Открываем сделку через API
            # Для демо-счета используется флаг is_demo=True (по умолчанию)
            trade_result = await client.buy(
                asset=current_asset,
                amount=trade_amount,
                direction=direction,
                expiration=expiration_time
            )
            
            logger.info(f"Сделка открыта: {trade_result}")
            
            # Ждём завершения сделки + небольшая пауза
            await asyncio.sleep(expiration_time + 5)
            
        except Exception as e:
            logger.error(f"Ошибка в торговом цикле: {e}")
            await asyncio.sleep(10)  # Пауза перед повторной попыткой
    
    logger.info("Торговый цикл остановлен.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")

def main():
    """Точка входа"""
    # Инициализация Pocket Option
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if not loop.run_until_complete(init_pocket_option()):
        print("Не удалось подключиться к Pocket Option. Проверьте SSID в коде")
        return
    
    # Создаём Telegram-бот
    token = TELEGRAM_BOT_TOKEN
    if not token or token == "ВСТАВЬТЕ_СЮДА_ТОКЕН_ОТ_BOTFATHER":
        print("Вы не вставили токен в код!")
        return
    
    application = Application.builder().token(token).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()