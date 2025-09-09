#  Precog API Usage and Evaluation Example

This example is demonstrates how to access Precog Subnet 55 outputs using an authenticated wallet (described in main README.md).  

Using this data and the Reference Rates from the Coin Metrics Community API, it calculates various error metrics, and simulates the impact of a trading strategy based on the Precog Forecasts.

# Prerequisites

## Python Packages
In addition to the prerequisites in the main precog-api-utility package, this example also utilizes the following packages installed with `pip`:
```
pandas
matplotlib
seaborn
coinmetrics-api-client
```

You will also need to have a bittensor wallet stored in your enviornment with the requisite Alpha token threshold, to authenticate the precog-api package.

### Instructions

First, ensure you have set up the precog-api as instructed in main README.md for this repo.

Then, from the top level of this repository first ensure you are in the virtual env, if not run:
```
source .venv/bin/activate
```
Install the additional packages:
```
pip install pandas matplotlib matplotlib coinmetrics-api-client
```

# Usage
The file `precog_analysis_utils.py` does not need to be accessed directly, unless you wish to modify the trading strategy used by the test.  

First you must ensure you have an authenticated access to token using `precog authenticate`, as described in the main repo README.md

The file `test_precog_module.py` can be executed in python to run the analysis.  It is set up so that it function as a Jupyter Notebook using Jupytext percent-formatted cells.  VSCode can also execute these as distinct cells.  

However this script can also be executed directly in the terminal and will print output to the terminal and generate the figures as popups, simply by running
```
python3 test_precog_module.py` 
```

It may take 5-15 minutes to pull all the data, depending on time frame considered.  By using a CoinMetrics API key to retrieve longer Reference Rate history the analysis can be extended up to 30 days, which is the maximum provided by the Precog API.

# Output

The output can be adjusted in the `test_precog_module.py` script, and will be cleaner to read in a notebook format.  The following shows the output of this script for 7 days from 2025-09-02 to 2025-09-09:

## Metrics Printed to Terminal

### Root Mean Squared (Percentage) Errors
The RMSE and RMSPE (percent error) of the predictions vs observed price; as well as the observed price at evaluation and prediction time for comparison:
```
RMSE between point_prediction and ReferenceRateUSD: 369.06922399787067
RMSE between ReferenceRateUSD @ Pred Time and Eval Time: 344.5885621103513

RMSPE between point_prediction and ReferenceRateUSD: 0.0033160366281946583
RMSPE between ReferenceRateUSD @ Pred Time and Eval Time: 0.0030949390507784653
```

### Mean Absolute Difference and Percent Error
```
MAD between point_prediction and ReferenceRateUSD: 236.69034078216058
MAD between ReferenceRateUSD @ Pred vs Eval time: 226.0004193256165

MAPE between point_prediction and ReferenceRateUSD: 0.002125724134755004
MAPE between ReferenceRateUSD @ Pred Time and Eval Time: 0.0020292235175914516
```

### Quantiles of the Percent of Prices included within average Interval Forecast
```
Percent of Price Values 1-hour after prediction falling within interval:
count    2001.000000
mean       65.303333
std        31.224101
min         0.000000
25%        41.666667
50%        75.000000
75%       100.000000
max       100.000000
```

### Relative Width of the Interval Forecast compared to the observed Price Range
```
Relative Width - Interval Pred / Price Range
count    2001.000000
mean        1.379930
std         0.948758
min        -0.771572
25%         0.792637
50%         1.152502
75%         1.729513
max        13.685625
```

### Trading simulation
The Trading Simulations use the following parameters by default:  Portfolio is initialized with a $100 wallet worth equal parts USD and BTC ($50/$50). 
At every prediction time a trade buys or sells, and the wallet can only buy BTC so long as it has a non-zero amount of USD and can only sell so long as it has a non-zero BTC balance.

There are three strategies tested:  A fixed-trade strategy that always buys or sells $1 based on the point forecast, a variable-trade strategy that scales from $0.2 to $5 depending on the width of the interval forecast (smaller trade with wider interval). And a no-trade strategy that holds the initial balance as a control for BTC price movement.

#### Final Balances
The first piece of info printed is the final portfolio value of each strategy:
```
No Trading Strat Final Bal: 101.52646957058388
Fixed Trade Final Bal: 101.65248942862789
Variable Trades Final Bal: 102.04931799933668
```
#### Max 24-h drop
Then the maximum drop value over 24-hours given by each strategy, as a measure of "riskiness"
```
hold
max 24h drop: 1.0056600204672463
fixed
max 24h drop: 0.9707933689399226
variable
max 24h drop: 1.0159752907008084
```

#### Minimum Portfolio value reached during simulation
(this week was a bull market)
```
Lowest Portfolio Value:
Holding BTC: 100.0
Fixed BTC Trading: 100.0
Variable BTC Trading: 100.0
```

#### Percent of times in window when one strategy beat another
```
Fixed Strategy Better than Holding BTC 1533 / 2003 times
Variable Strategy Better than Holding BTC 1524 / 2003 times
Variable Strategy Better than Fixed 1069 / 2003 times
```

## Figures
Additionally, the analysis figures of the Trading Simulation

### Total Portfolio value of different strategies over time
Possibly the most interesting information.  Shows how often one strategy out-performed another and what market conditions (dips or spikes) flip the trends
<img width="1000" height="500" alt="example_readme_1" src="https://github.com/user-attachments/assets/6e9c1333-cc84-4aad-8381-325b5c2bc9e1" />

### Histogram of Variable-Strategy Trade size 
Less interesting, but informative for the variable-trading strategy.  Shows the typical size of trades
<img width="640" height="480" alt="example_variable_trade_size" src="https://github.com/user-attachments/assets/7f693a26-094c-4b41-acf7-087785220042" />

### BTC vs USD balance of Fixed and Variable Strategies
Illustrates why different strategies had different values.  The different approaches can sell out of USD or BTC at different times depending on their trade size

<img width="1000" height="500" alt="example_fixed_portfolio" src="https://github.com/user-attachments/assets/0b58046c-beb3-4fb1-9c8b-c2136668219b" />
<img width="1000" height="500" alt="example_variable_portfolio" src="https://github.com/user-attachments/assets/67f35111-1a03-4029-990f-5c5157d37fa1" />
