# Beijing Stock Exchange (BSE) Data Scraper

A Python web-scraping script to fetch historical daily K-line (candlestick) data and tick-by-tick trade details for Beijing Stock Exchange (BSE) tickers from Sina Finance (sina.com.cn).

## Features

- **Historical K-line Data**: Fetch daily candlestick data including open, high, low, close prices and volume
- **Tick-by-Tick Trade Details**: Get real-time transaction data with timestamps, prices, volumes, and buy/sell direction
- **Real-time Quotes**: Access current market quotes with bid/ask prices and other market information
- **CSV Export**: Automatically save data to CSV files for further analysis
- **Error Handling**: Robust error handling for network issues and data parsing

## Installation

1. Clone this repository:
```bash
git clone https://github.com/pppicker/test.git
cd test
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the script with default example ticker:

```bash
python bse_scraper.py
```

Or specify a custom ticker:

```bash
python bse_scraper.py 430139
```

### Programmatic Usage

```python
from bse_scraper import BSEScraper

# Initialize the scraper
scraper = BSEScraper()

# Fetch K-line data for a BSE ticker
ticker = "430047"  # BSE ticker code (without exchange prefix)
kline_data = scraper.get_kline_data(ticker, scale="240", datalen=100)
print(kline_data.head())

# Fetch tick-by-tick trade details
tick_data = scraper.get_tick_data(ticker)
print(tick_data.head())

# Fetch real-time quote
quote = scraper.get_realtime_quote(ticker)
print(quote)
```

### Parameters

#### `get_kline_data(ticker, scale, ma, datalen)`

- `ticker` (str): BSE stock ticker symbol (e.g., '430047')
- `scale` (str): Time scale for K-line data
  - `"240"` - Daily (default)
  - `"60"` - Hourly
  - `"30"` - 30-minute
  - `"15"` - 15-minute
  - `"5"` - 5-minute
- `ma` (str): Moving average periods, comma-separated (default: "5,10,20,30")
- `datalen` (int): Number of data points to fetch (default: 1000)

**Returns**: pandas DataFrame with columns:
- `date`: Trading date/time
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume

#### `get_tick_data(ticker)`

- `ticker` (str): BSE stock ticker symbol (e.g., '430047')

**Returns**: pandas DataFrame with columns:
- `time`: Transaction time
- `price`: Transaction price
- `volume`: Transaction volume
- `type`: Original Chinese type indicator
- `direction`: English direction ('buy', 'sell', or 'neutral')

#### `get_realtime_quote(ticker)`

- `ticker` (str): BSE stock ticker symbol (e.g., '430047')

**Returns**: Dictionary with real-time quote information including:
- `name`: Stock name
- `open`: Opening price
- `current`: Current price
- `high`: Day's high
- `low`: Day's low
- `volume`: Trading volume
- `amount`: Trading amount
- And more...

## Output

The script automatically saves data to CSV files:
- `bse_{ticker}_kline.csv` - Historical K-line data
- `bse_{ticker}_ticks.csv` - Tick-by-tick trade details

## Example Output

```
============================================================
Beijing Stock Exchange Data Scraper - Sina Finance
============================================================

1. Fetching Historical K-line Data...
------------------------------------------------------------
Fetching K-line data for bj430047...
Successfully fetched 100 K-line data points

K-line Data (first 10 rows):
        date   open   high    low  close    volume
0 2024-01-02  10.50  10.80  10.40  10.75  12345678
1 2024-01-03  10.75  11.00  10.70  10.95  13456789
...

K-line data saved to: bse_430047_kline.csv

2. Fetching Tick-by-Tick Trade Details...
------------------------------------------------------------
Fetching tick-by-tick data for bj430047...
Successfully fetched 80 tick records

Tick Data (first 10 rows):
       time  price  volume    type direction
0  15:00:00  10.75   10000   买盘       buy
1  14:59:58  10.74    5000   卖盘      sell
...

Tick data saved to: bse_430047_ticks.csv

3. Fetching Real-time Quote...
------------------------------------------------------------
Fetching real-time quote for bj430047...
Successfully fetched real-time quote

Real-time Quote:
  name: 股票名称
  open: 10.50
  current: 10.75
  high: 10.80
  low: 10.40
  ...
```

## Requirements

- Python 3.7+
- requests >= 2.28.0
- pandas >= 1.5.0

## Notes

- The Beijing Stock Exchange uses the 'bj' prefix for ticker symbols on Sina Finance
- The script automatically adds the 'bj' prefix if not provided
- Rate limiting: Add delays between requests to avoid overwhelming the server
- Data availability depends on Sina Finance's data coverage for BSE stocks

## License

This project is open source and available under the MIT License.

## Disclaimer

This script is for educational and research purposes only. Please respect Sina Finance's terms of service and use responsibly. Ensure you have the right to scrape data from the website and comply with all applicable laws and regulations.