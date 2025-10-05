# Quick Start Guide

Get started with the BSE Scraper in 3 simple steps!

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Run the Basic Example

```bash
python bse_scraper.py
```

This will fetch data for the example ticker (430047) and save it to CSV files.

Or specify your own ticker:

```bash
python bse_scraper.py 430139
```

## 3. Use in Your Own Code

```python
from bse_scraper import BSEScraper

# Create scraper instance
scraper = BSEScraper()

# Fetch K-line data
ticker = "430047"  # Your BSE ticker code
kline_data = scraper.get_kline_data(ticker, scale="240", datalen=100)
print(kline_data.head())

# Fetch tick data
tick_data = scraper.get_tick_data(ticker)
print(tick_data.head())

# Fetch real-time quote
quote = scraper.get_realtime_quote(ticker)
print(quote)
```

## More Examples

Run the comprehensive examples:

```bash
python example_usage.py
```

This demonstrates:
- Multiple timeframes (daily, hourly, etc.)
- Tick-by-tick analysis
- Real-time monitoring
- Data export to CSV/JSON/Excel
- Error handling

## Common Use Cases

### Fetch Daily Data for Analysis

```python
scraper = BSEScraper()
df = scraper.get_kline_data("430047", scale="240", datalen=365)
df.to_csv("yearly_data.csv", index=False)
```

### Monitor Multiple Stocks

```python
scraper = BSEScraper()
tickers = ["430047", "430139", "430418"]

for ticker in tickers:
    quote = scraper.get_realtime_quote(ticker)
    if quote:
        print(f"{ticker}: Current={quote['current']}, Change={(quote['current']-quote['prev_close'])/quote['prev_close']*100:.2f}%")
```

### Analyze Recent Trades

```python
scraper = BSEScraper()
tick_df = scraper.get_tick_data("430047")

# Count buy vs sell
buy_count = len(tick_df[tick_df['direction'] == 'buy'])
sell_count = len(tick_df[tick_df['direction'] == 'sell'])
print(f"Buy/Sell Ratio: {buy_count/sell_count:.2f}")
```

## Timeframe Codes

Use these values for the `scale` parameter:

- `"240"` - Daily (1 day)
- `"60"` - Hourly (1 hour)
- `"30"` - 30 minutes
- `"15"` - 15 minutes
- `"5"` - 5 minutes

## Notes

- The ticker format is automatically converted (e.g., "430047" → "bj430047")
- Add delays between requests to be respectful of Sina's servers
- Data availability depends on Sina Finance's coverage
- Use the script responsibly and comply with terms of service

## Troubleshooting

**No data returned?**
- Verify the ticker code is correct
- Check if the ticker is listed on Beijing Stock Exchange
- Ensure you have internet connectivity

**Rate limiting?**
- Add `time.sleep(1)` between requests
- Reduce the number of concurrent requests

**Import errors?**
- Make sure you installed dependencies: `pip install -r requirements.txt`

## Running Tests

```bash
python -m unittest test_bse_scraper.py -v
```

All 7 tests should pass ✓

---

For more detailed information, see [README.md](README.md)
