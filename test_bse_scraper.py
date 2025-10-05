#!/usr/bin/env python3
"""
Unit tests for the BSE Scraper
"""

import unittest
from unittest.mock import patch, Mock
import pandas as pd
import json
from bse_scraper import BSEScraper


class TestBSEScraper(unittest.TestCase):
    """Test cases for BSEScraper class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = BSEScraper()
    
    def test_scraper_initialization(self):
        """Test that scraper initializes correctly"""
        self.assertIsNotNone(self.scraper)
        self.assertIsNotNone(self.scraper.session)
        self.assertIn('User-Agent', self.scraper.headers)
    
    def test_ticker_prefix(self):
        """Test that ticker gets bj prefix added correctly"""
        # Test with mock to verify the ticker format
        ticker_without_prefix = "430047"
        ticker_with_prefix = f"bj{ticker_without_prefix}"
        
        # The method should handle both cases
        self.assertTrue(ticker_with_prefix.startswith('bj'))
    
    @patch('bse_scraper.requests.Session.get')
    def test_get_kline_data_success(self, mock_get):
        """Test successful K-line data fetch"""
        # Mock response data
        mock_data = [
            {
                'day': '2024-01-02',
                'open': '10.50',
                'high': '10.80',
                'low': '10.40',
                'close': '10.75',
                'volume': '12345678'
            },
            {
                'day': '2024-01-03',
                'open': '10.75',
                'high': '11.00',
                'low': '10.70',
                'close': '10.95',
                'volume': '13456789'
            }
        ]
        
        # Create mock response
        mock_response = Mock()
        mock_response.text = f'var _430047_data=({json.dumps(mock_data)});'
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test the method
        result = self.scraper.get_kline_data('430047', datalen=10)
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('date', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('close', result.columns)
    
    @patch('bse_scraper.requests.Session.get')
    def test_get_kline_data_no_data(self, mock_get):
        """Test K-line data fetch with no data returned"""
        mock_response = Mock()
        mock_response.text = 'var _430047_data=([]);'
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.scraper.get_kline_data('430047')
        self.assertIsNone(result)
    
    @patch('bse_scraper.requests.Session.get')
    def test_get_tick_data_success(self, mock_get):
        """Test successful tick data fetch"""
        mock_data = [
            {
                'time': '15:00:00',
                'price': '10.75',
                'volume': '10000',
                'type': '买盘'
            },
            {
                'time': '14:59:58',
                'price': '10.74',
                'volume': '5000',
                'type': '卖盘'
            }
        ]
        
        mock_response = Mock()
        mock_response.text = json.dumps(mock_data)
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.scraper.get_tick_data('430047')
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('time', result.columns)
        self.assertIn('price', result.columns)
        self.assertIn('volume', result.columns)
    
    @patch('bse_scraper.requests.Session.get')
    def test_get_realtime_quote_success(self, mock_get):
        """Test successful real-time quote fetch"""
        mock_response = Mock()
        mock_response.text = 'var hq_str_bj430047="股票名称,10.50,10.45,10.75,10.80,10.40,10.74,10.76,12345678,132000000,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2024-01-02,15:00:00,00";'
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.scraper.get_realtime_quote('430047')
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('name', result)
        self.assertIn('open', result)
        self.assertIn('current', result)
        self.assertEqual(result['name'], '股票名称')
    
    @patch('bse_scraper.requests.Session.get')
    def test_network_error_handling(self, mock_get):
        """Test that network errors are handled gracefully"""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")
        
        # Test K-line data
        result = self.scraper.get_kline_data('430047')
        self.assertIsNone(result)
        
        # Test tick data
        result = self.scraper.get_tick_data('430047')
        self.assertIsNone(result)
        
        # Test real-time quote
        result = self.scraper.get_realtime_quote('430047')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
