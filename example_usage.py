#!/usr/bin/env python3
"""
Example usage of the BSE Scraper
Demonstrates different ways to use the scraper for various data fetching scenarios
"""

from bse_scraper import BSEScraper
import time


def example_basic_usage():
    """Basic usage example"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Usage - Single Ticker")
    print("="*70)
    
    scraper = BSEScraper()
    ticker = "430047"
    
    # Fetch daily K-line data
    print(f"\nFetching daily K-line data for {ticker}...")
    df = scraper.get_kline_data(ticker, scale="240", datalen=30)
    if df is not None:
        print(f"Retrieved {len(df)} data points")
        print(f"Latest trading day: {df['date'].iloc[0] if 'date' in df.columns else 'N/A'}")
        print(f"Latest close price: {df['close'].iloc[0] if 'close' in df.columns else 'N/A'}")


def example_multiple_timeframes():
    """Fetch K-line data for multiple timeframes"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Multiple Timeframes")
    print("="*70)
    
    scraper = BSEScraper()
    ticker = "430047"
    
    timeframes = {
        "240": "Daily",
        "60": "Hourly",
        "30": "30-minute",
        "15": "15-minute"
    }
    
    for scale, name in timeframes.items():
        print(f"\nFetching {name} data...")
        df = scraper.get_kline_data(ticker, scale=scale, datalen=20)
        if df is not None:
            print(f"  ✓ Retrieved {len(df)} {name} data points")
        else:
            print(f"  ✗ Failed to retrieve {name} data")
        time.sleep(0.5)  # Be nice to the server


def example_tick_analysis():
    """Analyze tick-by-tick data"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Tick-by-Tick Analysis")
    print("="*70)
    
    scraper = BSEScraper()
    ticker = "430047"
    
    print(f"\nFetching tick data for {ticker}...")
    df = scraper.get_tick_data(ticker)
    
    if df is not None and not df.empty:
        print(f"\nTotal ticks: {len(df)}")
        
        # Analyze buy/sell distribution if direction column exists
        if 'direction' in df.columns:
            buy_count = len(df[df['direction'] == 'buy'])
            sell_count = len(df[df['direction'] == 'sell'])
            neutral_count = len(df[df['direction'] == 'neutral'])
            
            print(f"\nTrade Distribution:")
            print(f"  Buy orders:     {buy_count:4d} ({buy_count/len(df)*100:.1f}%)")
            print(f"  Sell orders:    {sell_count:4d} ({sell_count/len(df)*100:.1f}%)")
            print(f"  Neutral orders: {neutral_count:4d} ({neutral_count/len(df)*100:.1f}%)")
        
        # Calculate average price if available
        if 'price' in df.columns:
            avg_price = df['price'].mean()
            print(f"\nAverage trade price: {avg_price:.2f}")
        
        # Show sample trades
        print(f"\nSample trades (first 5):")
        print(df.head())


def example_realtime_monitoring():
    """Monitor real-time quotes"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Real-time Quote Monitoring")
    print("="*70)
    
    scraper = BSEScraper()
    tickers = ["430047", "430139", "430418"]  # Multiple BSE tickers
    
    print("\nFetching real-time quotes for multiple tickers...\n")
    
    for ticker in tickers:
        quote = scraper.get_realtime_quote(ticker)
        if quote:
            print(f"{ticker} ({quote.get('name', 'N/A')})")
            print(f"  Current: {quote.get('current', 'N/A')}")
            print(f"  Open:    {quote.get('open', 'N/A')}")
            print(f"  High:    {quote.get('high', 'N/A')}")
            print(f"  Low:     {quote.get('low', 'N/A')}")
            print(f"  Volume:  {quote.get('volume', 'N/A')}")
            
            # Calculate change percentage
            if quote.get('current') and quote.get('prev_close'):
                change_pct = (quote['current'] - quote['prev_close']) / quote['prev_close'] * 100
                print(f"  Change:  {change_pct:+.2f}%")
            print()
        else:
            print(f"{ticker}: Failed to fetch quote\n")
        
        time.sleep(0.5)  # Be nice to the server


def example_data_export():
    """Export data to multiple formats"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Data Export")
    print("="*70)
    
    scraper = BSEScraper()
    ticker = "430047"
    
    print(f"\nFetching data for {ticker}...")
    
    # Fetch K-line data
    kline_df = scraper.get_kline_data(ticker, datalen=100)
    if kline_df is not None:
        # Export to CSV
        csv_file = f"example_output_{ticker}_kline.csv"
        kline_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"✓ K-line data exported to: {csv_file}")
        
        # Export to JSON
        json_file = f"example_output_{ticker}_kline.json"
        kline_df.to_json(json_file, orient='records', date_format='iso', indent=2)
        print(f"✓ K-line data exported to: {json_file}")
        
        # Export to Excel (if openpyxl is installed)
        try:
            excel_file = f"example_output_{ticker}_kline.xlsx"
            kline_df.to_excel(excel_file, index=False, engine='openpyxl')
            print(f"✓ K-line data exported to: {excel_file}")
        except ImportError:
            print("  (Excel export requires openpyxl: pip install openpyxl)")
    
    time.sleep(0.5)
    
    # Fetch tick data
    tick_df = scraper.get_tick_data(ticker)
    if tick_df is not None:
        csv_file = f"example_output_{ticker}_ticks.csv"
        tick_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"✓ Tick data exported to: {csv_file}")


def example_error_handling():
    """Demonstrate error handling"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Error Handling")
    print("="*70)
    
    scraper = BSEScraper()
    
    # Try with an invalid ticker
    print("\nAttempting to fetch data for invalid ticker...")
    invalid_ticker = "999999"
    result = scraper.get_kline_data(invalid_ticker)
    if result is None:
        print("✓ Gracefully handled invalid ticker")
    
    # Try with empty ticker
    print("\nAttempting to fetch data with empty ticker...")
    result = scraper.get_kline_data("")
    if result is None:
        print("✓ Gracefully handled empty ticker")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("BSE Scraper - Usage Examples")
    print("="*70)
    print("\nNote: These examples may fail if running in an environment")
    print("without internet access or if Sina Finance's API is unavailable.")
    print("="*70)
    
    # Run examples
    try:
        example_basic_usage()
        time.sleep(1)
        
        example_multiple_timeframes()
        time.sleep(1)
        
        example_tick_analysis()
        time.sleep(1)
        
        example_realtime_monitoring()
        time.sleep(1)
        
        example_data_export()
        time.sleep(1)
        
        example_error_handling()
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
    
    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70)


if __name__ == "__main__":
    main()
