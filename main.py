import os
import time
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier

# --- PASTE YOUR TELEGRAM CREDENTIALS HERE ---
TELEGRAM_BOT_TOKEN = "8982790552:AAHi_oOd6hPUwqSQej67PuMTo0o2tBmDvcE"
TELEGRAM_CHAT_ID = "8247289837
TICKERS = ["AAPL", "TSLA", "BTC-USD", "ETH-USD"]


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def analyze_asset(ticker):
    print(f"Analyzing {ticker}...")
    df = yf.download(ticker, period="3y", interval="1d", progress=False)

    if df.empty:
        return

    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)

    # Calculate indicators
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

    # Train Random Forest AI
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    # Calculate probability
    prediction = model.predict(X_latest)[0]
    prob_up = model.predict_proba(X_latest)[0][1] * 100
    latest_price = df["Close"].iloc[-1]

    if prediction == 1 and prob_up >= 60.0:
        msg = f"🚀 AI BUY SIGNAL: {ticker}\nPrice: ${latest_price:.2f}\nConfidence (UP): {prob_up:.1f}%"
        send_telegram(msg)
    elif prediction == 0 and prob_up <= 40.0:
        msg = f"🔻 AI SELL SIGNAL: {ticker}\nPrice: ${latest_price:.2f}\nConfidence (DOWN): {100 - prob_up:.1f}%"
        send_telegram(msg)


def run_bot():
    send_telegram("🤖 Cloud AI Trading Bot Active & Monitoring Assets!")
    while True:
        for ticker in TICKERS:
            try:
                analyze_asset(ticker)
            except Exception as e:
                print(f"Error on {ticker}: {e}")

        # Re-check market every 4 hours
        time.sleep(14400)


if __name__ == "__main__":
    run_bot()
