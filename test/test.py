# 导入pandas库，用于数据处理和分析
import pandas as pd
# 导入requests库，用于发送HTTP请求
import requests
# 导入datetime模块，用于日期处理
from datetime import datetime, timedelta
# 导入os模块，用于文件和路径操作
import os
# 导入json模块，用于处理JSON文件
import json
# 在文件顶部添加类型提示
from typing import Dict, Any, List, cast
# 导入time模块，用于控制延时
import time
# 导入io模块，用于处理字节流
import io
# 导入re模块，用于正则表达式处理
import re

# ---------------------------- 基本配置 ----------------------------
# 输入的Excel文件名，包含原始股票信息
INPUT_EXCEL = "stocks_info.xlsx"
# 输出的Excel文件名，用于保存分析结果
OUTPUT_EXCEL = "results/stocks_performance.xlsx"
# 北证50指数的代码
INDEX_CODE = "bj899050"  # 新浪财经使用的北证50指数代码
# 用于保存处理进度的文件
PROGRESS_FILE = "temp/analysis_progress.json"  # 用于保存处理进度的文件

# 新浪财经API的基本URL
SINA_STOCK_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{code}=/CN_MarketDataService.getKLineData"
SINA_INDEX_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{code}=/CN_MarketDataService.getKLineData"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/stock/"
}

def get_trading_dates():
    """获取中国A股市场交易日列表"""
    try:
        # 使用新浪财经API获取上证指数数据，从中提取交易日
        url = f"{SINA_INDEX_URL}?symbol=sh000001&scale=240&ma=no&datalen=100"
        response = requests.get(url, headers=HEADERS)
        
        # 解析JSONP响应
        data_str = response.text.strip()
        data_str = data_str.split("=(")[1].rsplit(");", 1)[0]
        data = json.loads(data_str)
        
        # 提取日期列表
        trading_dates = [item['day'] for item in data]
        return trading_dates
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        return []

def get_trading_date_range(date_str, offset=30):
    """获取指定日期后的交易日期范围"""
    try:
        # 获取所有交易日
        all_trading_dates = get_trading_dates()
        if not all_trading_dates:
            return None, None
            
        # 将输入日期转换为标准格式
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        target_date_str = target_date.strftime('%Y-%m-%d')
        
        # 找到大于等于目标日期的第一个交易日
        start_idx = -1
        for i, td in enumerate(all_trading_dates):
            if td >= target_date_str:
                start_idx = i
                break
                
        if start_idx == -1:
            return None, None
            
        # 计算结束日期
        end_idx = min(start_idx + offset - 1, len(all_trading_dates) - 1)
        
        return all_trading_dates[start_idx], all_trading_dates[end_idx]
    
    except Exception as e:
        print(f"获取交易日期范围失败: {e}")
        return None, None

def normalize_code_for_sina(code):
    """将股票代码转换为新浪财经API使用的格式"""
    if code.endswith('.BJ'):
        raw_code = code.replace('.BJ', '')
        return f"bj{raw_code}"  # 北交所代码格式 bj430090
    elif code[:2] in ["60", "68", "90"]:
        return f"sh{code[:6]}"  # 上证代码格式 sh600000
    elif code[:2] in ["00", "30", "20"]:
        return f"sz{code[:6]}"  # 深证代码格式 sz000001
    else:
        return f"bj{code[:6]}"  # 默认北交所格式

def get_stock_data(code, start_date, end_date):
    """从新浪财经获取股票历史数据"""
    try:
        # 添加延时避免请求过快
        time.sleep(1)
        
        # 转换股票代码为新浪格式
        sina_code = normalize_code_for_sina(code)
        
        # 计算日期差，获取足够多的数据点
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days_diff = (end - start).days + 5  # 多取几天作为余量
        
        # 构建API URL
        url = f"{SINA_STOCK_URL}?symbol={sina_code}&scale=240&ma=no&datalen={days_diff}"
        
        # 发送请求
        response = requests.get(url, headers=HEADERS)
        
        # 解析JSONP响应
        data_str = response.text.strip()
        match = re.search(r'=\((.*?)\);', data_str)
        if not match:
            print(f"无法解析响应数据: {data_str[:100]}...")
            return None
            
        data_json = match.group(1)
        data = json.loads(data_json)
        
        # 转换为DataFrame
        df = pd.DataFrame(data)
        
        # 过滤日期范围
        df['day'] = pd.to_datetime(df['day'])
        mask = (df['day'] >= pd.Timestamp(start_date)) & (df['day'] <= pd.Timestamp(end_date))
        df = df[mask]
        
        # 转换数值列
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        return df
    
    except Exception as e:
        print(f"获取股票数据失败: {e}")
        return None

def calculate_return(code, start_date, end_date):
    """计算指定股票在给定时间范围内的涨跌幅"""
    try:
        # 获取股票数据
        df = get_stock_data(code, start_date, end_date)
        
        # 如果没有数据，返回None
        if df is None or df.empty:
            print(f"未获取到股票 {code} 在 {start_date} 至 {end_date} 期间的数据")
            return None
        
        # 计算涨跌幅：（最后收盘价 - 首日收盘价）/ 首日收盘价 * 100
        df = df.sort_values('day')
        first_close = float(df.iloc[0]['close'])
        last_close = float(df.iloc[-1]['close'])
        
        return (last_close - first_close) / first_close * 100
    
    except Exception as e:
        # 打印错误信息
        print(f"计算{code}涨跌幅失败: {e}")
        return None

def calculate_index_return(start_date, end_date):
    """计算指数在给定时间范围内的涨跌幅"""
    try:
        # 先尝试获取北证50指数数据
        df = get_stock_data(INDEX_CODE, start_date, end_date)
        
        # 如果没有北证50指数数据，尝试使用上证指数
        if df is None or df.empty:
            print("未获取到北证50指数数据，尝试使用上证指数...")
            df = get_stock_data("sh000001", start_date, end_date)
        
        # 如果还是没有数据，返回None
        if df is None or df.empty:
            print(f"未获取到指数数据在 {start_date} 至 {end_date} 期间")
            return None
        
        # 计算指数涨跌幅
        df = df.sort_values('day')
        first_close = float(df.iloc[0]['close'])
        last_close = float(df.iloc[-1]['close'])
        
        return (last_close - first_close) / first_close * 100
    
    except Exception as e:
        # 打印错误信息
        print(f"计算指数涨跌幅失败: {e}")
        return None

def load_progress():
    """加载已处理的股票列表"""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"加载进度文件失败: {e}")
        return []

def save_progress(processed_codes):
    """保存已处理的股票列表"""
    try:
        # 确保文件目录存在
        directory = os.path.dirname(PROGRESS_FILE)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # 保存进度
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed_codes, f, ensure_ascii=False, indent=2)
        print(f"进度已保存到: {PROGRESS_FILE}")
    except Exception as e:
        print(f"保存进度文件失败: {e}")

def save_results_to_excel(results, file_path):
    """保存结果到Excel文件"""
    try:
        # 确保文件目录存在
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # 创建DataFrame并排序
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('相对涨跌幅', ascending=False)
        
        # 保存到Excel
        result_df.to_excel(file_path, index=False)
        print(f"结果已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存Excel失败: {e}")
        return False

def analyze_performance():
    """分析股票相对于指数的表现"""
    # 检查并读取输入文件
    if not os.path.exists(INPUT_EXCEL):
        print(f"未找到输入文件: {INPUT_EXCEL}")
        return
    
    # 读取Excel文件
    df = pd.read_excel(INPUT_EXCEL)
    
    # 加载已处理的股票列表
    processed_codes = load_progress()
    if processed_codes:
        print(f"发现已处理 {len(processed_codes)} 只股票的记录")
    
    # 初始化结果列表，添加类型提示
    results: List[Dict[str, Any]] = []
    
    # 如果输出文件存在，加载已有结果
    if os.path.exists(OUTPUT_EXCEL):
        try:
            existing_results = pd.read_excel(OUTPUT_EXCEL)
            # 使用 cast 来确保类型正确
            results = cast(List[Dict[str, Any]], existing_results.to_dict('records'))
            print(f"已加载现有结果文件中的 {len(results)} 条记录")
        except Exception as e:
            print(f"加载现有结果文件失败: {e}")
    
    # 遍历每只股票进行分析
    total_stocks = len(df)
    for current_idx, (_, row) in enumerate(df.iterrows(), 1):
        # 获取股票基本信息
        code = row['证券代码']
        name = row['证券简称']
        
        # 如果股票已处理，跳过
        if code in processed_codes:
            print(f"跳过已处理的股票: {code} {name}")
            continue
        
        announce_date = row['公告日期']
        
        print(f"\n{'-'*60}")
        print(f"进度: [{current_idx}/{total_stocks}]")
        print(f"股票信息: {code} {name}")
        print(f"公告日期: {announce_date}")
        print(f"{'-'*60}")
        
        try:
            # 获取交易日期范围
            start_date, end_date = get_trading_date_range(announce_date)
            if start_date is None or end_date is None:
                print(f"警告: 无法获取 {code} 的交易日期范围")
                continue
            
            print(f"计算区间: {start_date} 至 {end_date}")
            
            # 计算个股涨跌幅
            stock_return = calculate_return(code, start_date, end_date)
            if stock_return is None:
                print(f"警告: 无法获取 {code} 的股票行情数据")
                continue
            
            print(f"个股涨跌幅: {round(stock_return, 2)}%")
            
            # 计算指数涨跌幅
            index_return = calculate_index_return(start_date, end_date)
            if index_return is None:
                print(f"警告: 无法获取北证50指数行情数据")
                continue
            
            print(f"指数涨跌幅: {round(index_return, 2)}%")
            
            # 计算相对涨跌幅
            relative_return = stock_return - index_return
            print(f"相对涨跌幅: {round(relative_return, 2)}%")
            
            # 添加分析结果
            result: Dict[str, Any] = {
                '证券代码': code,
                '证券简称': name,
                '公告日期': announce_date,
                '区间涨跌幅': round(stock_return, 2),
                '指数涨跌幅': round(index_return, 2),
                '相对涨跌幅': round(relative_return, 2),
                '开始日期': start_date,
                '结束日期': end_date
            }
            
            # 保存单条结果到列表
            results.append(result)
            
            # 更新进度
            processed_codes.append(code)
            save_progress(processed_codes)
            
            # 实时保存结果到Excel
            if save_results_to_excel(results, OUTPUT_EXCEL):
                print(f"数据已保存: {code} {name}")
            
        except Exception as e:
            print(f"处理 {code} 时发生错误: {e}")
            continue
    
    print(f"\n{'-'*60}")
    print(f"处理完成! 共处理 {total_stocks} 只股票，成功分析 {len(results)} 只")
    
    # 最终排序并保存
    try:
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('相对涨跌幅', ascending=False)
        result_df.to_excel(OUTPUT_EXCEL, index=False)
        print("最终结果已按相对涨跌幅排序完成")
    except Exception as e:
        print(f"最终排序保存时发生错误: {e}")

    # 处理完所有数据后，清除进度文件
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

# 程序入口点
if __name__ == "__main__":
    analyze_performance()