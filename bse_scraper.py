#!/usr/bin/env python3
"""
Beijing Stock Exchange (BSE) Data Scraper from Sina Finance
This script fetches historical daily K-line (candlestick) data and tick-by-tick trade details
for specified Beijing Stock Exchange tickers from sina.com.cn
"""

import requests
import pandas as pd
import json
from datetime import datetime
from typing import Optional, Dict, List
import time


class BSEScraper:
    """Scraper for Beijing Stock Exchange data from Sina Finance"""
    
    def __init__(self):
        self.base_url = "https://finance.sina.com.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://finance.sina.com.cn',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_kline_data(self, ticker: str, scale: str = "240", ma: str = "5,10,20,30", 
                       datalen: int = 1000) -> Optional[pd.DataFrame]:
        """
        Fetch historical daily K-line (candlestick) data
        
        Args:
            ticker: BSE stock ticker symbol (e.g., 'bj430047' for 430047.BJ)
            scale: Time scale for K-line (240 for daily, 60 for hourly, etc.)
            ma: Moving average periods (comma-separated)
            datalen: Number of data points to fetch
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        # Sina uses different prefixes for different exchanges
        # Beijing Stock Exchange uses 'bj' prefix
        if not ticker.startswith('bj'):
            ticker = f'bj{ticker}'
        
        # Sina K-line data API endpoint
        url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_bj{ticker.replace('bj', '')}_data=/CN_MarketDataService.getKLineData"
        
        params = {
            'symbol': ticker,
            'scale': scale,
            'ma': ma,
            'datalen': datalen
        }
        
        try:
            print(f"Fetching K-line data for {ticker}...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse JSONP response
            content = response.text
            # Extract JSON from JSONP callback
            if 'var _' in content and '=(' in content:
                json_start = content.find('=') + 1
                json_end = content.rfind(')')
                if json_start > 0 and json_end > json_start:
                    json_str = content[json_start:json_end].strip()
                    if json_str.startswith('('):
                        json_str = json_str[1:]
                    data = json.loads(json_str)
                else:
                    print("Failed to extract JSON from JSONP response")
                    return None
            else:
                data = json.loads(content)
            
            if not data or len(data) == 0:
                print(f"No data returned for ticker {ticker}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Rename columns to standard names
            column_mapping = {
                'day': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Convert numeric columns
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convert date column
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            print(f"Successfully fetched {len(df)} K-line data points")
            return df
            
        except requests.RequestException as e:
            print(f"Request error while fetching K-line data: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def get_tick_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Fetch tick-by-tick trade details (real-time transaction data)
        
        Args:
            ticker: BSE stock ticker symbol (e.g., 'bj430047' for 430047.BJ)
            
        Returns:
            DataFrame with columns: time, price, volume, type (buy/sell)
        """
        # Ensure ticker has bj prefix
        if not ticker.startswith('bj'):
            ticker = f'bj{ticker}'
        
        # Sina tick data API endpoint
        url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_Transactions.getTransactions"
        
        params = {
            'symbol': ticker,
            'num': 80,  # Number of recent transactions to fetch
        }
        
        try:
            print(f"Fetching tick-by-tick data for {ticker}...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse JSON response
            data = json.loads(response.text)
            
            if not data or len(data) == 0:
                print(f"No tick data returned for ticker {ticker}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Rename columns
            column_mapping = {
                'time': 'time',
                'price': 'price',
                'volume': 'volume',
                'type': 'type'
            }
            
            # Check which columns exist and rename them
            existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # Convert numeric columns
            if 'price' in df.columns:
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            # Add readable type (buy/sell/neutral)
            if 'type' in df.columns:
                df['direction'] = df['type'].map({
                    '买盘': 'buy',
                    '卖盘': 'sell',
                    '中性盘': 'neutral',
                })
            
            print(f"Successfully fetched {len(df)} tick records")
            return df
            
        except requests.RequestException as e:
            print(f"Request error while fetching tick data: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def get_realtime_quote(self, ticker: str) -> Optional[Dict]:
        """
        Fetch real-time quote information
        
        Args:
            ticker: BSE stock ticker symbol (e.g., 'bj430047' for 430047.BJ)
            
        Returns:
            Dictionary with real-time quote data
        """
        if not ticker.startswith('bj'):
            ticker = f'bj{ticker}'
        
        # Sina real-time quote API
        url = f"https://hq.sinajs.cn/list={ticker}"
        
        try:
            print(f"Fetching real-time quote for {ticker}...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            content = response.text
            
            # Parse the response format: var hq_str_bj430047="name,open,prev_close,..."
            if '="' in content:
                data_str = content.split('="')[1].rstrip('";\n')
                parts = data_str.split(',')
                
                if len(parts) > 10:
                    quote_data = {
                        'name': parts[0],
                        'open': float(parts[1]) if parts[1] else None,
                        'prev_close': float(parts[2]) if parts[2] else None,
                        'current': float(parts[3]) if parts[3] else None,
                        'high': float(parts[4]) if parts[4] else None,
                        'low': float(parts[5]) if parts[5] else None,
                        'bid': float(parts[6]) if parts[6] else None,
                        'ask': float(parts[7]) if parts[7] else None,
                        'volume': float(parts[8]) if parts[8] else None,
                        'amount': float(parts[9]) if parts[9] else None,
                        'date': parts[30] if len(parts) > 30 else None,
                        'time': parts[31] if len(parts) > 31 else None,
                    }
                    print(f"Successfully fetched real-time quote")
                    return quote_data
            
            print(f"Failed to parse real-time quote data")
            return None
            
        except requests.RequestException as e:
            print(f"Request error while fetching real-time quote: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


def main():
    """Example usage of the BSE scraper"""
    # Initialize scraper
    scraper = BSEScraper()
    
    # Example Beijing Stock Exchange ticker
    # Note: Replace with actual BSE ticker code
    ticker = "430047"  # Will be converted to bj430047
    
    print("=" * 60)
    print("Beijing Stock Exchange Data Scraper - Sina Finance")
    print("=" * 60)
    print()
    
    # Fetch K-line data
    print("\n1. Fetching Historical K-line Data...")
    print("-" * 60)
    kline_df = scraper.get_kline_data(ticker, scale="240", datalen=100)
    if kline_df is not None and not kline_df.empty:
        print("\nK-line Data (first 10 rows):")
        print(kline_df.head(10))
        
        # Save to CSV
        output_file = f"bse_{ticker}_kline.csv"
        kline_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nK-line data saved to: {output_file}")
    else:
        print("Failed to fetch K-line data")
    
    # Wait a bit between requests
    time.sleep(1)
    
    # Fetch tick-by-tick data
    print("\n2. Fetching Tick-by-Tick Trade Details...")
    print("-" * 60)
    tick_df = scraper.get_tick_data(ticker)
    if tick_df is not None and not tick_df.empty:
        print("\nTick Data (first 10 rows):")
        print(tick_df.head(10))
        
        # Save to CSV
        output_file = f"bse_{ticker}_ticks.csv"
        tick_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nTick data saved to: {output_file}")
    else:
        print("Failed to fetch tick data")
    
    # Wait a bit between requests
    time.sleep(1)
    
    # Fetch real-time quote
    print("\n3. Fetching Real-time Quote...")
    print("-" * 60)
    quote = scraper.get_realtime_quote(ticker)
    if quote:
        print("\nReal-time Quote:")
        for key, value in quote.items():
            print(f"  {key}: {value}")
    else:
        print("Failed to fetch real-time quote")
    
    print("\n" + "=" * 60)
    print("Data fetching completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
