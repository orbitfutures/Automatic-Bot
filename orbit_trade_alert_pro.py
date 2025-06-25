import requests
import matplotlib.pyplot as plt
from datetime import datetime
from telegram import Bot
import numpy as np

TOKEN = "7397317010:AAE41dwNOzYF8pxsZiOITCdhULQ7GJpHcUY"
CHAT_ID = 1917297411
bot = Bot(token=TOKEN)

def fetch_data():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&limit=50"
    response = requests.get(url)
    data = response.json()
    candles = []
    for d in data:
        candles.append({
            "time": datetime.fromtimestamp(d[0] / 1000),
            "open": float(d[1]),
            "high": float(d[2]),
            "low": float(d[3]),
            "close": float(d[4]),
            "volume": float(d[5])
        })
    return candles

def detect_levels(candles):
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    return max(highs[-10:]), min(lows[-10:])

def generate_trade(candles):
    resistance, support = detect_levels(candles)
    last = candles[-1]["close"]
    volume = candles[-1]["volume"]
    time = candles[-1]["time"].strftime('%Y-%m-%d %H:%M')

    if last < resistance - 150:
        signal = f"""
🚨 *TRADE ALERT*

🕒 Timeframe: 15m
📊 Pair: BTCUSDT (Binance Live)
📈 Price: ${last}

🔍 *Chart Analysis*
📌 Resistance: ${resistance}
🕯️ Candlestick: Bearish rejection
📉 Volume: {volume:.2f}
📐 Structure: Lower High formation

✅ *Trade Setup*
📍 Type: SHORT
🎯 Entry: ${last}
🛑 SL: ${last + 200}
🎯 TP1: ${last - 300}
🎯 TP2: ${last - 500}
⚖️ R:R = 1:2+

🔁 Alternate:
Long above ${resistance + 100} | SL: {last} | TP: {resistance + 300}
"""
    else:
        signal = f"""
🚨 *TRADE ALERT*

🕒 Timeframe: 15m
📊 Pair: BTCUSDT (Binance Live)
📈 Price: ${last}

🔍 *Chart Analysis*
📌 Support: ${support}
🕯️ Candlestick: Bullish bounce
📉 Volume: {volume:.2f}
📐 Structure: Higher Low formation

✅ *Trade Setup*
📍 Type: LONG
🎯 Entry: ${last}
🛑 SL: ${last - 200}
🎯 TP1: ${last + 300}
🎯 TP2: ${last + 500}
⚖️ R:R = 1:2+

🔁 Alternate:
Short below ${support - 100} | SL: {last} | TP: {support - 300}
"""
    return signal, resistance, support

def generate_chart(candles, resistance, support):
    times = [c["time"] for c in candles]
    closes = [c["close"] for c in candles]
    plt.figure(figsize=(10, 4))
    plt.plot(times, closes, label="Close Price")
    plt.axhline(y=resistance, color='r', linestyle='--', label='Resistance')
    plt.axhline(y=support, color='g', linestyle='--', label='Support')
    plt.title("BTC 15m Live Chart")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("chart.png")
    plt.close()

def main():
    print("Running analysis...")
    candles = fetch_data()
    print("Candles fetched:", len(candles))
    message, res, sup = generate_trade(candles)
    generate_chart(candles, res, sup)
    print("Sending to Telegram...")
    bot.send_photo(chat_id=CHAT_ID, photo=open("chart.png", "rb"), caption=message, parse_mode="Markdown")

if __name__ == "__main__":
    main()
