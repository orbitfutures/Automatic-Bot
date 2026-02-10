import os

import pandas as pd
import requests
from dotenv import load_dotenv
from ta.momentum import RSIIndicator
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = str(os.getenv("CHAT_ID"))

DELTA_API_KEY = os.getenv("DELTA_API_KEY")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET")
MODE = os.getenv("MODE", "testnet")

# Delta endpoints
if MODE == "testnet":
    DELTA_BASE = "https://testnet-api.delta.exchange"
else:
    DELTA_BASE = "https://api.delta.exchange"


# -------------------------------
# Fetch candles from Delta
# -------------------------------
def get_candles(symbol="BTCUSDT", interval="15m", limit=100):
    # Delta uses product_id, so we will use a simple mapping:
    # BTCUSDT -> BTCUSDT perpetual (example id might vary)
    # For now, we use Binance candles as fallback if Delta fails.
    try:
        # fallback to Binance for candle feed (stable)
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&limit={limit}"
        )
        data = requests.get(url, timeout=10).json()

        df = pd.DataFrame(
            data,
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "qav",
                "trades",
                "tbbav",
                "tbqav",
                "ignore",
            ],
        )

        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        return df
    except Exception:
        return None


# -------------------------------
# Signal Engine (RSI + Trend)
# -------------------------------
def generate_signal(df):
    if df is None or len(df) < 50:
        return None

    close = df["close"]
    rsi = RSIIndicator(close, window=14).rsi()

    last_close = close.iloc[-1]
    last_rsi = rsi.iloc[-1]

    # simple trend using EMA
    ema_fast = close.ewm(span=20).mean()
    ema_slow = close.ewm(span=50).mean()

    trend = "BULLISH" if ema_fast.iloc[-1] > ema_slow.iloc[-1] else "BEARISH"

    # Setup logic
    if last_rsi < 30 and trend == "BULLISH":
        side = "LONG"
    elif last_rsi > 70 and trend == "BEARISH":
        side = "SHORT"
    else:
        side = "WAIT"

    return {
        "close": last_close,
        "rsi": float(last_rsi),
        "trend": trend,
        "side": side,
    }


# -------------------------------
# Setup Builder (Entry, SL, TP)
# -------------------------------
def build_trade_setup(signal):
    price = signal["close"]
    side = signal["side"]

    if side == "WAIT":
        return None

    # 1:2 RR
    risk = price * 0.003  # 0.3% risk

    if side == "LONG":
        entry = price
        sl = price - risk
        tp1 = price + risk
        tp2 = price + (risk * 2)

    else:
        entry = price
        sl = price + risk
        tp1 = price - risk
        tp2 = price - (risk * 2)

    return {
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
    }


# -------------------------------
# Telegram Handlers
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    del context
    await update.message.reply_text(
        "🔥 Orbit_Trade Bot Active!\n\nSend: Trade\nTo get latest BTC setup."
    )


async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    del context
    await update.message.reply_text("⏳ Analyzing BTCUSDT 15m chart...")

    df = get_candles("BTCUSDT", "15m", 120)
    signal = generate_signal(df)

    if not signal:
        await update.message.reply_text("⚠️ Not enough data.")
        return

    setup = build_trade_setup(signal)

    msg = (
        f"📊 Orbit_Trade Setup (BTCUSDT - 15m)\n\n"
        f"Trend: {signal['trend']}\n"
        f"RSI(14): {signal['rsi']:.2f}\n\n"
        f"Signal: {signal['side']}\n\n"
    )

    if setup is None:
        msg += "❌ No high probability trade right now.\nWait for next candle."
    else:
        msg += (
            "✅ Trade Setup\n\n"
            f"Side: {setup['side']}\n"
            f"Entry: {setup['entry']:.2f}\n"
            f"Stop Loss: {setup['sl']:.2f}\n"
            f"TP1: {setup['tp1']:.2f}\n"
            f"TP2: {setup['tp2']:.2f}\n\n"
            "Risk Reward: 1:2\n"
        )

    await update.message.reply_text(msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if text == "trade":
        await trade_command(update, context)
    else:
        await update.message.reply_text("Send 'Trade' to get the latest setup.")


# -------------------------------
# Main
# -------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Orbit_Trade Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
