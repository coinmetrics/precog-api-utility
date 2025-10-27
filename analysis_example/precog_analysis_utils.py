# -*- coding: utf-8 -*-
"""BT_Miner_Analysis Module"""
# core.py - Main analysis and trading functions

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Callable

from coinmetrics.api_client import CoinMetricsClient

class MinerAnalysis:
    from typing import Dict


import pandas as pd
from coinmetrics.api_client import CoinMetricsClient  # Assuming this is your API client


class MinerAnalysis:
    def __init__(self, cm_api_key: str):
        self.client = CoinMetricsClient(cm_api_key)

    # CoinMetrics functions
    def get_reference_rates(self, start: str, end: str) -> pd.DataFrame:
        """Get reference rates from CoinMetrics"""
        return self.client.get_asset_metrics(
            assets="btc",
            metrics="ReferenceRateUSD",
            frequency="1m",
            start_time=start,
            end_time=end,
        ).to_dataframe()

    # Data processing
    def merge_market_data(
        self, miner_df: pd.DataFrame, rr_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge miner data with reference rates"""
        pred_rr = pd.merge(
            miner_df, rr_df, left_on="prediction_time", right_on="time", how="left"
        )
        pred_rr = pred_rr.rename(columns={"ReferenceRateUSD": "RR_pred_time"}).drop(
            columns=["time", "asset"]
        )
        pred_rr = pd.merge(
            pred_rr, rr_df, left_on="evaluation_time", right_on="time", how="left"
        )
        pred_rr = pred_rr.rename(columns={"ReferenceRateUSD": "RR_eval_time"}).drop(
            columns=["time", "asset"]
        )

        pred_rr = self._add_diff_columns(pred_rr)
        return pred_rr

    def _add_diff_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add difference columns (internal helper)"""
        df["diff_pred"] = df.point_prediction - df.RR_pred_time
        df["diff_obs"] = df.RR_eval_time - df.RR_pred_time
        return df

    # Analysis functions
    def calculate_entropy(
        self, df: pd.DataFrame, bins: int = 10, range: List[Tuple[float, float]] = None
    ) -> float:
        """Calculate prediction entropy using 2D histogram to analyze randomness"""
        if range is None:
            range = [
                [df.diff_obs.min(), df.diff_obs.max()],
                [df.diff_pred.min(), df.diff_pred.max()],
            ]

        H, *_ = np.histogram2d(
            df.diff_obs, df.diff_pred, bins=[bins, bins], range=range
        )
        p = H / H.sum()
        mask = p != 0
        S = -np.nansum(p[mask] * np.log2(p[mask])) / np.log(
            (~miner_df.diff_pred.isna()).sum()
        )
        return S

    def prepare_trading_preds(
        self, miner_data: pd.DataFrame, top_N: int
    ) -> pd.DataFrame:
        """
        Aggregate top N miner predictions for trading simulation
        """
        miner_data = (
            miner_data.groupby("prediction_time")
            .apply(lambda x: x.nlargest(top_N, "avg_reward"))
            .reset_index(drop=True)
        )
        return miner_data


# plotting.py - Visualization functions


class TradingSimulator:
    def __init__(
        self,
        strategy: Callable[Dict, Dict],
        initial_usd: float = 1000,
        initial_btc_usd_value: float = 1000,
        strategy_params: dict = {},
    ):
        """
        Initialize the Trading Simulator.

        :param strategy: A function that takes miner data and returns trade volume.
        :param initial_usd: Initial USD balance.
        :param initial_btc: Initial BTC balance.
        :param strategy_params: Dict w/ parameters for each strategy
        """
        self.strategy = strategy
        self.initial_usd = initial_usd
        self.initial_btc_usd_value = initial_btc_usd_value
        self.strategy_params = strategy_params

    def simulate(
        self,
        miner_preds: pd.DataFrame,
        prices: pd.DataFrame,
        start_time: pd.Timestamp,
        duration_days: int = 7,
        wallet_floor=True,
    ) -> pd.DataFrame:
        """
        Run the trading simulation.

        :param miner_preds: DataFrame containing aggregated miner Precog predictions
        :param prices: DataFrame returned by coinmetrics API client of ReferenceRates
        :param start_time: Simulation start time.
        :param duration_days: Number of days to run the simulation.
        :param wallet_floor: Boolean to block trades that put balance into negative.
        :return: DataFrame with timestamps and portfolio values.
        """

        # Define simulation end time
        max_end_time = miner_preds.prediction_time.max()
        end_time = min(start_time + timedelta(days=duration_days), max_end_time)

        # Initialize portfolio state
        portfolio = []
        current_ts = start_time
        usd_bal = self.initial_usd

        # Get initial BTC price

        btc_price = prices.loc[prices.time == current_ts, "ReferenceRateUSD"].iloc[0]
        btc_bal = self.initial_btc_usd_value / btc_price

        # Store initial portfolio state
        portfolio.append(
            {
                "timestamp": current_ts,
                "trade_vol": 0,
                "usd_balance": usd_bal,
                "btc_balance": btc_bal,
                "btc_price": btc_price,
            }
        )

        # Simulate trading over time
        while current_ts < end_time:
            current_ts += timedelta(minutes=5)
            current_pred = miner_preds.loc[miner_preds.prediction_time == current_ts]
            btc_price = prices.loc[prices.time == current_ts, "ReferenceRateUSD"].iloc[
                0
            ]

            if current_pred.empty:
                print(f"Skip {current_ts}. No Pred")
                continue

            current_bal = usd_bal + (btc_bal * btc_price)
            current_values = {
                "current_pred": current_pred,
                "current_ts": current_ts,
                "btc_price": btc_price,
                "current_bal": current_bal,
                "usd_bal": usd_bal,
                "btc_bal": btc_bal
            }
            # Use the strategy function to determine trade volume
            trade = self.strategy(
                current_values, self.strategy_params
            )

            # Propose trade
            new_usd = usd_bal - trade
            new_btc = btc_bal + (trade / btc_price)

            # No trade if insufficient wallet balance
            if wallet_floor and (new_usd < 0 or new_btc < 0):
                trade = 0
                new_usd = usd_bal - trade
                new_btc = btc_bal + (trade / btc_price)

            usd_bal = new_usd
            btc_bal = new_btc

            # Record portfolio state
            portfolio.append(
                {
                    "timestamp": current_ts,
                    "trade_vol": trade,
                    "usd_balance": usd_bal,
                    "btc_balance": btc_bal,
                    "btc_price": btc_price,
                }
            )

        # Convert results to DataFrame
        portfolio_df = pd.DataFrame(portfolio)
        portfolio_df["total_bal_usd"] = (
            portfolio_df["usd_balance"]
            + portfolio_df["btc_balance"] * portfolio_df["btc_price"]
        )

        return portfolio_df


# Trading simulation
def fixed_volume_strat(
    current_values: Dict,
    strategy_params: dict,
) -> float:
    """
    Implement buy/sell fixed strategy
    Returns: USD amount to trade (positive = buy BTC, negative = sell BTC)
    """
    miner_preds = current_values["current_pred"]
    price = current_values["btc_price"]
    
    min_perc = strategy_params["min_perc"]
    volume = strategy_params["volume"]

    agg_pred = miner_preds[["point_prediction"]].mean()["point_prediction"]

    perc_chg = (agg_pred - price) / price

    if perc_chg > min_perc:
        return volume
    elif perc_chg < -min_perc:
        return -volume
    return 0.0

def fixed_percent_strat(
    current_values: Dict,
    strategy_params: dict,
) -> float:
    """
    Implement buy/sell fixed strategy
    Returns: USD amount to trade (positive = buy BTC, negative = sell BTC)
    """
    miner_preds = current_values["current_pred"]
    price = current_values["btc_price"]
    balance = current_values["current_bal"]
    usd_bal = current_values["usd_bal"]
    btc_bal = current_values["btc_bal"]
    
    min_perc = strategy_params["min_perc"]
    volume_percent = strategy_params["volume_percent"]

    agg_pred = miner_preds[["point_prediction"]].mean()["point_prediction"]

    perc_chg = (agg_pred - price) / price

    if perc_chg > min_perc:
        return volume_percent * usd_bal
    elif perc_chg < -min_perc:
        return -volume_percent * btc_bal * price
    return 0.0


def var_vol_intv_strat(
    current_values: Dict,
    strategy_params: dict,
) -> float:
    miner_preds = current_values["current_pred"]
    
    min_perc = strategy_params["min_perc"]
    min_trade_size = strategy_params["min_trade_size"]
    max_trade_size = strategy_params["max_trade_size"]
    base_volume = strategy_params["volume"]
    STANDARD_RANGE = strategy_params["standard_range"]

    agg_interval = miner_preds[
        ["point_prediction", "interval_lower", "interval_upper"]
    ].mean()

    trade_binary = fixed_volume_strat(current_values, strategy_params)

    predicted_range = agg_interval["interval_upper"] - agg_interval["interval_lower"]
    trade_size = STANDARD_RANGE / predicted_range
    trade_size = np.clip(trade_size, min_trade_size, max_trade_size)

    return trade_size * trade_binary



def hold_only(
    current_values: Dict,
    strategy_params: dict,
) -> float:
    """
    Implement non-trading strategy (hold-only)
    Returns: USD amount to trade (positive = buy BTC, negative = sell BTC)
    """
    return 0


class MinerVisualization:
    @staticmethod
    def plot_strategy_performance(trade_df: pd.DataFrame):
        """Plot trading strategy results"""
        fig, ax = plt.subplots()
        ax.plot(trade_df.timestamp, trade_df.total_usd, label="Strategy")
        ax.plot(trade_df.timestamp, trade_df.btc_hold_value, label="BTC Hold")
        ax.set_ylabel("Portfolio Value (USD)")
        ax.legend()
        return fig  # config.py - Configuration
