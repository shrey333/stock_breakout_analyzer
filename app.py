from pathlib import Path

import appdirs as ad

CACHE_DIR = ".cache"

# Force appdirs to say that the cache dir is .cache
ad.user_cache_dir = lambda *args: CACHE_DIR

# Create the cache dir if it doesn't exist
Path(CACHE_DIR).mkdir(exist_ok=True)

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io


def analyze_breakout_strategy(
    symbol: str,
    start_date: str,
    end_date: str,
    volume_threshold: float,
    price_change_threshold: float,
    holding_period: int,
) -> pd.DataFrame:
    # Fetch data
    stock = yf.Ticker(symbol)
    df = stock.history(start=start_date, end=end_date)

    if df.empty:
        st.error(f"No data found for {symbol} between {start_date} and {end_date}")
        return None

    # Calculate volume moving average
    df["volume_ma_20"] = df["Volume"].rolling(window=20).mean()

    # Calculate daily returns
    df["daily_return"] = df["Close"].pct_change()

    # Calculate volume ratio
    df["volume_ratio"] = (df["Volume"] / df["volume_ma_20"] - 1) * 100  # as percentage

    # Identify breakout days
    breakout_conditions = (
        df["Volume"] > df["volume_ma_20"] * (1 + volume_threshold / 100)
    ) & (  # Volume condition
        df["daily_return"] > price_change_threshold / 100
    )  # Price condition

    breakout_dates = df[breakout_conditions].index

    # Calculate returns for each breakout
    breakout_returns = []
    for breakout_date in breakout_dates:
        try:
            # Get the price data for holding period after breakout
            start_idx = df.index.get_loc(breakout_date)
            end_idx = start_idx + holding_period

            if end_idx >= len(df):
                continue

            entry_price = df.iloc[start_idx]["Close"]
            exit_price = df.iloc[end_idx]["Close"]

            # Calculate return
            holding_period_return = (exit_price - entry_price) / entry_price

            breakout_returns.append(
                {
                    "Breakout Date": breakout_date.strftime("%Y-%m-%d"),
                    "Volume": int(df.loc[breakout_date, "Volume"]),
                    "20d Avg Volume": int(df.loc[breakout_date, "volume_ma_20"]),
                    "Volume % Above Avg": round(
                        df.loc[breakout_date, "volume_ratio"], 2
                    ),
                    "Price Change %": round(
                        df.loc[breakout_date, "daily_return"] * 100, 2
                    ),
                    "Entry Price": round(entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    f"{holding_period}d Return %": round(
                        holding_period_return * 100, 2
                    ),
                }
            )

        except Exception as e:
            st.warning(f"Error processing breakout date {breakout_date}: {e}")

    # Convert results to DataFrame
    results_df = pd.DataFrame(breakout_returns)

    if len(results_df) == 0:
        st.info(f"No breakout conditions met for {symbol}")
        return None

    return results_df


def main():
    st.title("Advanced Stock Breakout Analyzer")
    st.write("Analyze stocks based on volume and price breakouts with detailed metrics")

    # User inputs
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Stock Symbol", "AAPL").upper()
        today = datetime.now().date()
        default_start = today - timedelta(days=365)
        start_date = st.date_input("Start Date", default_start, max_value=today)
    with col2:
        volume_threshold = st.number_input(
            "Volume Threshold (% above 20-day average)",
            min_value=50,
            value=200,
            help="Example: 200 means volume must be 200% above the 20-day average",
        )
        end_date = st.date_input("End Date", today, max_value=today)

    col3, col4 = st.columns(2)
    with col3:
        price_change_threshold = st.number_input(
            "Price Change Threshold (%)",
            min_value=0.1,
            value=2.0,
            help="Minimum price increase percentage required",
        )
    with col4:
        holding_period = st.number_input(
            "Holding Period (Days)",
            min_value=1,
            value=10,
            help="Number of days to hold after breakout",
        )

    if st.button("Analyze Breakouts"):
        with st.spinner("Analyzing breakout patterns..."):
            results = analyze_breakout_strategy(
                symbol=symbol,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                volume_threshold=volume_threshold,
                price_change_threshold=price_change_threshold,
                holding_period=holding_period,
            )

            if results is not None:
                # Summary statistics
                st.subheader("Summary Statistics")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Breakouts", len(results))
                with col2:
                    avg_return = results[f"{holding_period}d Return %"].mean()
                    st.metric(
                        f"Average {holding_period}-day Return", f"{avg_return:.2f}%"
                    )
                with col3:
                    win_rate = (results[f"{holding_period}d Return %"] > 0).mean() * 100
                    st.metric("Win Rate", f"{win_rate:.1f}%")

                # Additional statistics
                col4, col5 = st.columns(2)
                with col4:
                    st.metric(
                        "Best Return",
                        f"{results[f'{holding_period}d Return %'].max():.2f}%",
                    )
                with col5:
                    st.metric(
                        "Worst Return",
                        f"{results[f'{holding_period}d Return %'].min():.2f}%",
                    )

                st.subheader("Breakout Analysis Results")
                st.dataframe(results)

                # Download button
                csv = results.to_csv(index=False)
                st.download_button(
                    label="Download Results CSV",
                    data=csv,
                    file_name=f"{symbol}_breakout_analysis.csv",
                    mime="text/csv",
                )


if __name__ == "__main__":
    main()
