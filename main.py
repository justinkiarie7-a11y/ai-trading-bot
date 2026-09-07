import os
import time
import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# Fetch API keys safely from environment variables (No GitHub scanner alerts)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Public Binance API endpoints to prevent cloud IP blocks
PAIRS = {
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD"
}

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Missing Telegram credentials in environment variables.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram alert error: {e}")

def fetch_crypto_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=300"
    res = requests.get(url, timeout=10)
    data = res.json()
    
    df = pd.DataFrame(data, columns=[
        "Open_time", "Open", "High", "Low", "Close", "Volume",
        "Close_time", "Quote_asset_volume", "Number_of_trades",
        "Taker_buy_base", "Taker_buy_quote", "Ignore"
    ])
    df["Close"] = df["Close"].astype(float)
    return df

def analyze_asset(symbol_name, binance_symbol):
    print(f"Analyzing {symbol_name}...")
    df = fetch_crypto_data(binance_symbol)
    
    if df.empty:
        return

    # Technical Indicators
    df["Return_1D"] = df["Close"].pct_change(1)
    df["Return_5D"] = df["Close"].pct_change(5)
    df["Return_10D"] = df["Close"].pct_change(10)
    df["MA_Ratio"] = df["Close"] / df["Close"].rolling(window=20).mean()
    df["Volatility"] = df["Return_1D"].rolling(window=20).std()

    # Target: 1 if price goes UP tomorrow
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    df = df.dropna()

    features = ["Return_1D", "Return_5D", "Return_10D", "MA_Ratio", "Volatility"]

    X_train = df[features].iloc[:-1]
    y_train = df["Target"].iloc[:-1]
    X_latest = df[features].iloc[[-1]]

    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    prediction = model.predict(X_latest)[0]
    prob_up = model.predict_proba(X_latest)[0][1] * 100
    latest_price = df["Close"].iloc[-1]

    if prediction == 1 and prob_up >= 60.0:
        msg = f"🚀 AI BUY SIGNAL: {symbol_name}\nPrice: ${latest_price:.2f}\nConfidence (UP): {prob_up:.1f}%"
        send_telegram(msg)
    elif prediction == 0 and prob_up <= 40.0:
        msg = f"🔻 AI SELL SIGNAL: {symbol_name}\nPrice: ${latest_price:.2f}\nConfidence (DOWN): {100 - prob_up:.1f}%"
        send_telegram(msg)

def run_bot():
    send_telegram("🤖 Cloud AI Trading Bot Active & Monitoring Assets!")
    while True:
        for symbol, name in PAIRS.items():
            try:
                analyze_asset(name, symbol)
            except Exception as e:
                print(f"Error analyzing {name}: {e}")

        # Scan market every 4 hours
        time.sleep(14400)

if __name__ == "__main__":
    run_bot()

