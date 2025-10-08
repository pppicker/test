#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
北交所股票历史K线数据爬虫
作者: pppicker
日期: 2025-10-03
功能: 根据股票代码爬取北交所股票历史K线数据
"""

import akshare as ak
import pandas as pd
import os
import datetime
import time
import argparse
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from typing import Optional


class BeijingStockExchangeCrawler:
    """北交所股票历史K线数据爬虫类"""
    
    def __init__(self):
        """初始化方法"""
        self.data_folder = "stock_data"
        # 确保数据文件夹存在
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
    
    def get_stock_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """获取北交所股票历史K线数据，使用新浪财经接口。

        参数:
            stock_code: 6位北交所股票代码（以8开头）
            start_date: 开始日期，YYYYMMDD 或 YYYY-MM-DD，默认一年前
            end_date: 结束日期，YYYYMMDD 或 YYYY-MM-DD，默认今天

        返回:
            pandas.DataFrame 或 None
        """
        import requests
        import json
        import re
        
        # 校验代码
        if len(stock_code) != 6 or (not stock_code.isdigit()) or (not stock_code.startswith("8")):
            raise ValueError(f"股票代码 {stock_code} 无效，需为以8开头的6位数字")

        code = stock_code
        
        # 使用实际的当前日期，而不是未来日期
        now = datetime.datetime.now()
        today = now.strftime("%Y%m%d")

        def normalize(d: Optional[str]) -> Optional[str]:
            if not d:
                return None
            ds = str(d).replace("-", "").strip()
            if len(ds) != 8 or not ds.isdigit():
                raise ValueError(f"日期格式错误: {d}，应为 YYYYMMDD 或 YYYY-MM-DD")
            return ds

        end_s = normalize(end_date) or today
        start_s = normalize(start_date) or (now - datetime.timedelta(days=365)).strftime("%Y%m%d")

        # 确保不会查询未来日期
        if end_s > today:
            end_s = today
        if start_s > end_s:
            end_dt = datetime.datetime.strptime(end_s, "%Y%m%d")
            start_s = (end_dt - datetime.timedelta(days=30)).strftime("%Y%m%d")

        print(f"正在获取 {code} 从 {start_s} 到 {end_s} 的历史K线数据...")

        try:
            # 尝试新浪财经API
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            }
            
            # 新浪财经的API URL，北交所使用bj前缀
            url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_bj{code}_240_1681234567890=/CN_MarketDataService.getKLineData"
            
            params = {
                'scale': '240',  # 日K线
                'ma': 'no',
                'datalen': '1023'
            }
            
            print(f"尝试新浪财经API: {url}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 解析JSONP响应
            content = response.text
            print(f"响应内容预览: {content[:200]}...")
            
            # 提取JSON数据
            json_match = re.search(r'var.*?=\((.*?)\);?$', content)
            if not json_match:
                print(f"无法解析新浪财经响应数据")
            else:
                data = json.loads(json_match.group(1))
                
                if data and len(data) > 0:
                    # 转换为DataFrame
                    df_data = []
                    for item in data:
                        if isinstance(item, dict):
                            df_data.append({
                                '日期': item.get('day', ''),
                                '开盘': float(item.get('open', 0)),
                                '最高': float(item.get('high', 0)),
                                '最低': float(item.get('low', 0)),
                                '收盘': float(item.get('close', 0)),
                                '成交量': float(item.get('volume', 0)),
                                '成交额': float(item.get('amount', 0))
                            })
                    
                    if df_data:
                        stock_data = pd.DataFrame(df_data)
                        
                        # 日期过滤
                        if '日期' in stock_data.columns:
                            stock_data['日期'] = pd.to_datetime(stock_data['日期'])
                            start_date_dt = datetime.datetime.strptime(start_s, "%Y%m%d")
                            end_date_dt = datetime.datetime.strptime(end_s, "%Y%m%d")
                            
                            mask = (stock_data['日期'] >= start_date_dt) & (stock_data['日期'] <= end_date_dt)
                            stock_data = stock_data.loc[mask].reset_index(drop=True)
                            
                            if not stock_data.empty:
                                n_rows = len(stock_data)
                                print(f"成功获取 {code} 的历史K线数据，共 {n_rows} 条记录")
                                return stock_data
        
            # 如果新浪API失败，尝试AkShare
            print(f"新浪API失败，尝试AkShare接口...")
            
            # 尝试 BJ 专用接口
            bj_daily_func = getattr(ak, 'stock_zh_bj_daily', None)
            if callable(bj_daily_func):
                try:
                    sd = bj_daily_func(symbol=code, start_date=start_s, end_date=end_s)
                    if isinstance(sd, pd.DataFrame) and not sd.empty:
                        print(f"使用 stock_zh_bj_daily 获取数据成功")
                        return sd
                except Exception as e:
                    print(f"调用 stock_zh_bj_daily 失败: {e}")

            # 回退到通用接口
            try:
                sd2 = ak.stock_zh_a_hist(
                    symbol=f"{code}.BJ",
                    period="daily", 
                    start_date=start_s,
                    end_date=end_s,
                    adjust="qfq",
                )
                if isinstance(sd2, pd.DataFrame) and not sd2.empty:
                    print(f"使用 stock_zh_a_hist 获取数据成功")
                    return sd2
            except Exception as e:
                print(f"调用 stock_zh_a_hist 失败: {e}")
            
        except Exception as e:
            print(f"获取数据时出错: {e}")
            
        print(f"警告: 未找到股票 {code} 的数据，请检查股票代码或调整日期范围")
        return None
    
    def save_data(self, stock_code, data, file_format='csv'):
        """
        保存股票数据
        
        参数:
            stock_code: 股票代码
            data: DataFrame 包含股票数据
            file_format: 保存格式，支持 'csv' 和 'excel'
        """
        if data is None or data.empty:
            print("没有数据可保存")
            return False
            
        try:
            file_name = os.path.join(self.data_folder, f"{stock_code}")
            
            if file_format.lower() == 'csv':
                file_path = f"{file_name}.csv"
                data.to_csv(file_path, index=False, encoding='utf-8-sig')
                
            elif file_format.lower() == 'excel':
                file_path = f"{file_name}.xlsx"
                data.to_excel(file_path, index=False, engine='openpyxl')
                
            else:
                print(f"不支持的文件格式: {file_format}")
                return False
                
            print(f"数据已保存到 {file_path}")
            return True
            
        except Exception as e:
            print(f"保存数据时出错: {e}")
            return False
    
    def plot_kline(self, stock_code, data):
        """
        绘制K线图
        
        参数:
            stock_code: 股票代码
            data: DataFrame 包含股票数据
        """
        if data is None or data.empty:
            print("没有数据可绘制")
            return
            
        try:
            # 转换日期列为datetime类型
            data['日期'] = pd.to_datetime(data['日期'])
            
            # 创建图形
            plt.figure(figsize=(14, 7))
            
            # 绘制K线图(蜡烛图)
            for i in range(len(data)):
                # 当日收盘价高于开盘价，绘制红色K线
                if data['收盘'].iloc[i] >= data['开盘'].iloc[i]:
                    color = 'red'
                # 当日收盘价低于开盘价，绘制绿色K线
                else:
                    color = 'green'
                
                # 绘制实体部分
                plt.bar(i, data['收盘'].iloc[i] - data['开盘'].iloc[i], 
                       bottom=data['开盘'].iloc[i], color=color, width=0.6)
                
                # 绘制上下影线
                plt.plot([i, i], [data['最低'].iloc[i], data['最高'].iloc[i]], 
                        color='black', linewidth=1)
            
            # 设置x轴刻度和标签
            step = max(1, len(data)//10)  # 防止步长为0
            plt.xticks(range(0, len(data), step), 
                      [d.strftime('%Y-%m-%d') for d in data['日期'].iloc[::step]], 
                      rotation=45)
            
            # 添加标题和标签
            plt.title(f'北交所股票 {stock_code} K线图', fontsize=15)
            plt.xlabel('日期')
            plt.ylabel('价格')
            plt.grid(True, alpha=0.3)
            
            # 保存图片
            img_path = os.path.join(self.data_folder, f"{stock_code}_kline.png")
            plt.tight_layout()
            plt.savefig(img_path)
            plt.close()
            
            print(f"K线图已保存到 {img_path}")
            
        except Exception as e:
            print(f"绘制K线图时出错: {e}")
    
    def validate_stock_code(self, stock_code):
        """
        验证股票代码是否是北交所的股票
        
        参数:
            stock_code: 股票代码
        
        返回:
            bool: 是否是有效的北交所股票代码
        """
        if len(stock_code) != 6:
            return False
        
        if not stock_code.isdigit():
            return False
            
        # 北交所股票代码通常以8开头
        if not stock_code.startswith("8"):
            return False
            
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='北交所股票历史K线数据爬虫')
    parser.add_argument('stock_code', type=str, nargs='?', help='股票代码，如 830946；不提供则进入自检模式')
    parser.add_argument('--start', type=str, default=None, help='开始日期，格式YYYYMMDD或YYYY-MM-DD，默认为一年前')
    parser.add_argument('--end', type=str, default=None, help='结束日期，格式YYYYMMDD或YYYY-MM-DD，默认为今天')
    parser.add_argument('--format', type=str, default='csv', choices=['csv', 'excel'], help='保存格式，默认为csv')
    parser.add_argument('--plot', action='store_true', help='是否绘制K线图')
    parser.add_argument('--selftest', action='store_true', help='运行内置测试用例，验证抓取是否正常')

    args = parser.parse_args()

    crawler = BeijingStockExchangeCrawler()

    # 自检模式：未提供股票代码或显式 --selftest
    if args.selftest or not args.stock_code:
        samples = ["836433", "833533", "871981"]
        # 使用实际的当前日期
        now = datetime.datetime.now()
        today = now.strftime("%Y%m%d")
        start = (now - datetime.timedelta(days=60)).strftime("%Y%m%d")
        
        print(f"自检模式开始，日期范围: {start} 到 {today}")
        ok = 0
        for code in samples:
            print("\n====== 自检用例 ======")
            print(f"股票代码: {code}")
            df = crawler.get_stock_data(code, start, today)
            if isinstance(df, pd.DataFrame) and not df.empty:
                ok += 1
                print("数据示例:")
                print(df.head())
            time.sleep(1)  # 添加延时避免请求过快
        print(f"\n自检完成：{ok}/{len(samples)} 个用例成功。")
        return

    # 正常路径：校验代码并抓取
    if not crawler.validate_stock_code(args.stock_code):
        print(f"错误: {args.stock_code} 不是有效的北交所股票代码，请检查后重试")
        return

    # 获取股票数据
    stock_data = crawler.get_stock_data(args.stock_code, args.start, args.end)
    if stock_data is None or stock_data.empty:
        print("未获取到数据。")
        return

    # 保存数据
    crawler.save_data(args.stock_code, stock_data, args.format)

    # 如果需要，绘制K线图
    if args.plot:
        crawler.plot_kline(args.stock_code, stock_data)

    # 显示数据样例
    print("\n数据样例 (前5行):")
    print(stock_data.head())

if __name__ == '__main__':
    main()