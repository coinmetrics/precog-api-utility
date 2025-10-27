# -*- coding: utf-8 -*-
"""test_precog_module

Runs Trading Simulation using Precog Forecasts
"""

# %%
import precog_analysis_utils as pau
from precog_api import PrecogClient

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import sys
import os
import time

# %%
# Constants

COINMETRICS_API_KEY = ''# os.getenv("CM_API_KEY", "")

DAYS = 7
END_DATA = datetime.now().strftime("%Y-%m-%d")
START_DATA = (datetime.now() - pd.DateOffset(days=DAYS)).strftime("%Y-%m-%d")
LIMIT = 10000000

# %%
analyst = pau.MinerAnalysis(cm_api_key=COINMETRICS_API_KEY)

# %%
# Add api client to path if in Docker Container
os.environ["API_URL"] = "https://precog-api.coinmetrics.io"
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
)

client = PrecogClient()

has_next = True
data = []
page = 1
while has_next:
    result = client.get_historical_predictions(
        start_date=pd.to_datetime(START_DATA, utc=True),
        end_date=pd.to_datetime(START_DATA, utc=True) + pd.DateOffset(days=30),
        page=page,
    )
    data.extend(result["data"])
    time.sleep(0.2)  # To respect API rate limits

    print(
        f"Page: {page}/{result['pagination']['total_pages']} | Records: {len(data)}",
        end="\r",
    )
    page = result["pagination"]["current_page"] + 1
    has_next = result["pagination"]["has_next"]

predictions = pd.DataFrame(data)

predictions["prediction_time"] = pd.to_datetime(
    predictions["prediction_time"], utc=True
)
predictions["evaluation_time"] = pd.to_datetime(
    predictions["evaluation_time"], utc=True
)

# %%
rr_data = analyst.get_reference_rates(
    start=predictions.prediction_time.min(), end=predictions.evaluation_time.max()
)
# %%
# top_N = 1 # : good
top_N = 20
miner_preds = analyst.prepare_trading_preds(predictions, top_N)

miner_preds

# %%
# Statistical Analysis

agg_pred = miner_preds.groupby("prediction_time")[
    ["point_prediction", "interval_lower", "interval_upper", "evaluation_time"]
].mean()

price_pred = pd.merge(rr_data, agg_pred, left_on="time", right_on="prediction_time")

price_pred["relative_pred"] = (
    price_pred["point_prediction"] - price_pred["ReferenceRateUSD"]
) / price_pred["ReferenceRateUSD"]

print(price_pred.head())

# %%
# Calculate RMSE between miner_preds.point_prediction and rr_data.ReferenceRateUSD

align_pred_future_rr = pd.merge(
    agg_pred[["evaluation_time", "point_prediction"]],
    rr_data,
    left_on="evaluation_time",
    right_on="time",
    suffixes=("_pred", "_rr"),
)

price_pred_eval = pd.merge(
    price_pred[["time", "ReferenceRateUSD"]],
    price_pred[["evaluation_time", "ReferenceRateUSD"]],
    left_on="time",
    right_on="evaluation_time",
    suffixes=("_pred", "_eval"),
)


rmse = np.sqrt(
    (
        (
            align_pred_future_rr["ReferenceRateUSD"]
            - align_pred_future_rr["point_prediction"]
        )
        .pow(2)
        .mean()
    )
)
print(f"RMSE between point_prediction and ReferenceRateUSD: {rmse}")

rmse_rr_PvE_times = np.sqrt(
    (
        (
            price_pred_eval["ReferenceRateUSD_eval"]
            - price_pred_eval["ReferenceRateUSD_pred"]
        )
        .pow(2)
        .mean()
    )
)
print(f"RMSE between ReferenceRateUSD @ Pred Time and Eval Time: {rmse_rr_PvE_times}")

rmspe_pred_rr = np.sqrt(
    (
        (
            align_pred_future_rr["ReferenceRateUSD"]
            - align_pred_future_rr["point_prediction"]
        )
        / align_pred_future_rr["ReferenceRateUSD"]
    )
    .pow(2)
    .mean()
)
print(f"RMSPE between point_prediction and ReferenceRateUSD: {rmspe_pred_rr}")

rmspe_rr_PvE_times = np.sqrt(
    (
        (
            price_pred_eval["ReferenceRateUSD_eval"]
            - price_pred_eval["ReferenceRateUSD_pred"]
        )
        / price_pred_eval["ReferenceRateUSD_pred"]
    )
    .pow(2)
    .mean()
)
print(f"RMSPE between ReferenceRateUSD @ Pred Time and Eval Time: {rmspe_rr_PvE_times}")

# %%
# Calculate MAPE between miner_preds.point_prediction and rr_data.ReferenceRateUSD
mad = (
    (
        align_pred_future_rr["ReferenceRateUSD"]
        - align_pred_future_rr["point_prediction"]
    ).abs()
).mean()
print(f"MAD between point_prediction and ReferenceRateUSD: {mad}")

mad = (
    (
        price_pred_eval["ReferenceRateUSD_eval"]
        - price_pred_eval["ReferenceRateUSD_pred"]
    ).abs()
).mean()
print(f"MAD between ReferenceRateUSD @ Pred vs Eval time: {mad}\n")


mape = (
    (
        align_pred_future_rr["ReferenceRateUSD"]
        - align_pred_future_rr["point_prediction"]
    ).abs()
    / align_pred_future_rr["ReferenceRateUSD"]
).sum() / align_pred_future_rr.shape[0]
print(f"MAPE between point_prediction and ReferenceRateUSD: {mape}")


mape = (
    (
        price_pred_eval["ReferenceRateUSD_eval"]
        - price_pred_eval["ReferenceRateUSD_pred"]
    ).abs()
    / price_pred_eval["ReferenceRateUSD_pred"]
).sum() / price_pred_eval.shape[0]
print(f"MAPE between ReferenceRateUSD @ Pred Time and Eval Time: {mape}")

# %%
# Interval Prediction Analysis
# Calculate the percentage of times the actual price falls within the 
# predicted interval in the 1-hour window after the prediction time


def calculate_percentage_in_interval(row, price_pred):
    initial_time = row["time"]
    interval_lower = row["interval_lower"]
    interval_upper = row["interval_upper"]

    # Find the 1-hour window after the initial time
    one_hour_later = initial_time + pd.Timedelta(hours=1)
    if one_hour_later > price_pred.time.max():
        return np.nan

    window = price_pred[
        (price_pred["time"] > initial_time) & (price_pred["time"] <= one_hour_later)
    ]

    # Count the number of times ReferenceRateUSD is within the interval
    count_in_interval = window[
        (window["ReferenceRateUSD"] >= interval_lower)
        & (window["ReferenceRateUSD"] <= interval_upper)
    ].shape[0]

    # Calculate the percentage
    percentage = (
        (count_in_interval / window.shape[0]) * 100 if window.shape[0] > 0 else 0
    )  # Handle empty windows

    return percentage, count_in_interval

def calculate_min_max_interval(row, price_pred):
    initial_time = row["time"]

    # Find the 1-hour window after the initial time
    one_hour_later = initial_time + pd.Timedelta(hours=1)

    if one_hour_later > price_pred.time.max():
        return np.nan

    window = price_pred[
        (price_pred["time"] > initial_time) & (price_pred["time"] <= one_hour_later)
    ]

    if window.shape[0] <= 1:
        return np.nan

    # min-max price in interval
    real_range = window["ReferenceRateUSD"].max() - window["ReferenceRateUSD"].min()

    return real_range

# Apply the function to each row in price_pred
price_pred["interval_width"] = (
    price_pred["interval_upper"] - price_pred["interval_lower"]
)

price_pred[["percentage_in_interval", "count_in_interval"]] = price_pred.apply(
    lambda row: calculate_percentage_in_interval(row, price_pred),
    axis=1,
    result_type="expand",
)

price_pred["price_range_1h"] = price_pred.apply(
    lambda row: calculate_min_max_interval(row, price_pred), axis=1
)

price_pred["relative_width"] = price_pred.interval_width / price_pred.price_range_1h

print("Percent of Price Values 1-hour after prediction falling within interval:")
print(price_pred.percentage_in_interval.describe(), "\n")

print("Relative Width - Interval Pred / Price Range")
print(price_pred.relative_width.describe())


# %%
# TRADING SIMULATION

times_with_rates = predictions.prediction_time >= rr_data.time.min()
start_sim = predictions.loc[times_with_rates, "prediction_time"].min()
print(f"Simulation Start Time: {start_sim}")
# Depending on API key, one of the two data types might be limited. 
# Make sure we start at a time with Ref Rates

sim_days = DAYS
trade_vol = 1.0
vol_perc = 0.02

init_usd = 50
init_btc = 50
wallet_floor = True
min_perc = 0.0

# Run trading simulation
init_usd2 = 0
init_btc2 = 100

# params for variable trades
# [0.1, 5.0]
min_vol = 0.2
max_vol = 5.0
standard_range = 200

param_dict = {
    "min_perc": min_perc,
    "volume": trade_vol,
    "volume_percent": vol_perc,
    "min_trade_size": min_vol,
    "max_trade_size": max_vol,
    "standard_range": standard_range,
}


# %%
# Run Fixed-Vol trading simulation - buy/sell `trade_vol`

fixed_vol_strat = pau.TradingSimulator(
    # pau.fixed_volume_strat,
    pau.fixed_percent_strat,
    initial_usd=init_usd,
    initial_btc_usd_value=init_btc,
    strategy_params=param_dict,
)

fixed_vol_results = fixed_vol_strat.simulate(
    miner_preds,
    rr_data,
    start_time=pd.to_datetime(start_sim, utc=True),
    duration_days=sim_days,
    wallet_floor=wallet_floor,
)

print("Fixed Vol Sim done")
# %%
# Run Variable-Vol trading simulation - buy/sell variable amount based interval pred
variable_vol_strat = pau.TradingSimulator(
    pau.var_vol_intv_strat,
    initial_usd=init_usd,
    initial_btc_usd_value=init_btc,
    strategy_params=param_dict,
)

variable_vol_results = variable_vol_strat.simulate(
    miner_preds,
    rr_data,
    start_time=pd.to_datetime(start_sim, utc=True),
    duration_days=sim_days,
    wallet_floor=wallet_floor,
)

print("Variable Vol Sim done")

# %%
print('Trade Vol Sizes - Variable Strategy')
plt.figure()
variable_vol_results.trade_vol.hist()

# %%
# Run Holding simulation - no buys/sell
no_trading = pau.TradingSimulator(
    pau.hold_only,
    initial_usd=init_usd,
    initial_btc_usd_value=init_btc,
    strategy_params=param_dict,
)


no_trading_results = no_trading.simulate(
    miner_preds,
    rr_data,
    start_time=pd.to_datetime(start_sim, utc=True),
    duration_days=sim_days,
    wallet_floor=wallet_floor,
)

print("No Trade Sim done")

# %%
final_total = fixed_vol_results.total_bal_usd.iloc[-1]
final_price = fixed_vol_results.btc_price.iloc[-1]

print(f"No Trading Strat Final Bal: {no_trading_results['total_bal_usd'].iloc[-1]}")
print(f"Fixed Trade Final Bal: {final_total}")

final_total_var = variable_vol_results.total_bal_usd.iloc[-1]
final_price_var = variable_vol_results.btc_price.iloc[-1]

print(f"Variable Trades Final Bal: {final_total_var}")

# %%
# Assuming fixed_vol_results is your DataFrame with 'timestamp', 'total_bal_usd', and 'btc_price' columns

# Create the plot
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.set_ylabel("Total Portfolio Value (USD)")

sns.lineplot(
    x="timestamp",
    y="total_bal_usd",
    data=fixed_vol_results,
    ax=ax1,
    label="Fixed Size Trading BTC-init",
    legend=False,
    color="blue",
)

sns.lineplot(
    x="timestamp",
    y="total_bal_usd",
    data=variable_vol_results,
    ax=ax1,
    label="Variable Size Trading BTC-init",
    legend=False,
    color="red",
)


sns.lineplot(
    x="timestamp",
    y="total_bal_usd",
    data=no_trading_results,
    ax=ax1,
    label="Hold Initial Balance",
    legend=False,
    color="orange",
)

# sns.lineplot(x='timestamp', y='total_bal_usd', data=hold_results_usd, ax=ax1,
#              label='Breakeven', legend=False, color='black')


# Customize the plot
plt.title("Total Balance and BTC Price Over Time")
# plt.title('Net Change in Total Balance')
plt.xlabel("Timestamp")
# fig.legend(loc="upper right", bbox_to_anchor=(0.92, 0.5))
fig.legend()
plt.xticks(rotation=45)
plt.tight_layout()

plt.show()

# %%
# Calculate a the maximum 24H drawdown in a price time series on a rolling basis

def calculate_max_drawdown(df, window=24):
    """
    Calculates the maximum drawdown over a rolling window.

    Args:
        df: DataFrame with 'total_bal_usd' (or 'btc_price') column and a datetime index.
        window: Rolling window size in hours (default=24).

    Returns:
        DataFrame with an additional 'max_drawdown' column.
    """
    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index("timestamp")
        df.index = pd.to_datetime(df.index)

    # Shift by window hours → compares current value with value `window` hours earlier
    past = df["total_bal_usd"].shift(freq=f"{window}h")

    # Difference (current – past)
    diff = df["total_bal_usd"] - past

    # Max drawdown is the *minimum* of that rolling difference
    df["diff_24h"] = diff.rolling(f"{window}h").min()

    return df


i = 0

for result in [no_trading_results, fixed_vol_results, variable_vol_results]:
    name = ["hold", "fixed", "variable"]
    drop = calculate_max_drawdown(result, 24)  # Calculate 24-hour rolling max drawdown
    print(name[i])
    print("max 24h drop:", drop.diff_24h.max())
    i += 1

# %%
print("Lowest Portfolio Value:")
print(f"Holding BTC: {no_trading_results.total_bal_usd.min()}")
print(f"Fixed BTC Trading: {fixed_vol_results.total_bal_usd.min()}")
print(f"Variable BTC Trading: {variable_vol_results.total_bal_usd.min()}")


# %%
better = sum(fixed_vol_results["total_bal_usd"] > no_trading_results["total_bal_usd"])
total = fixed_vol_results.shape[0]
print(f"Fixed Strategy Better than Holding BTC {better} / {total} times")

better = sum(
    variable_vol_results["total_bal_usd"] > no_trading_results["total_bal_usd"]
)
total = variable_vol_results.shape[0]
print(f"Variable Strategy Better than Holding BTC {better} / {total} times")

better = sum(variable_vol_results["total_bal_usd"] > fixed_vol_results["total_bal_usd"])
total = variable_vol_results.shape[0]
print(f"Variable Strategy Better than Fixed {better} / {total} times")


# %%
def plot_usd_btc_bal(results_df, subtitle=''):
    # Create the plot
    fig2, ax3 = plt.subplots(figsize=(10, 5))
    results_df["btc_balance_usd"] = results_df["btc_balance"] * results_df["btc_price"]

    # Plot total_bal_usd on the left y-axis
    sns.lineplot(
        x="timestamp",
        y="usd_balance",
        data=results_df,
        ax=ax3,
        label="USD Wallet Balance",
    )
    sns.lineplot(
        x="timestamp",
        y="btc_balance_usd",
        data=results_df,
        ax=ax3,
        label="BTC Balance (USD Units)",
    )
    ax3.set_ylabel("Wallet Value (USD)")

    plt.title(f"USD & BTC Wallet Balances - {subtitle}")
    plt.tight_layout()

    plt.show()


plot_usd_btc_bal(fixed_vol_results, subtitle='Fixed Volume Strategy')

plot_usd_btc_bal(variable_vol_results, subtitle='Variable Volume Strategy')


# %%
