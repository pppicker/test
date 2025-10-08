# 导入pandas库，用于数据处理和分析
import pandas as pd
# 导入requests库，用于HTTP请求
import requests
# 导入datetime模块，用于日期处理
from datetime import datetime, timedelta
# 导入os模块，用于文件和路径操作
import os
# 导入json模块，用于处理JSON文件
import json
# 在文件顶部添加类型提示
from typing import Dict, Any, List, cast, Optional, Tuple, Union
# 导入time模块，用于控制延时
import time
# 导入正则表达式模块
import re
# 导入urllib.parse用于URL编码
import urllib.parse
# 导入openpyxl，用于Excel文件的高级操作
import openpyxl
from openpyxl.utils import get_column_letter

# ---------------------------- 基本配置 ----------------------------
# 输入的Excel文件名，包含原始股票信息
INPUT_EXCEL = "stocks_info.xlsx"
# 输出的Excel文件名，用于保存分析结果
OUTPUT_EXCEL = "stocks_performance.xlsx"
# 北证50指数的代码
INDEX_CODE = "899050"  # 新浪财经北证50指数代码
# 股票名称到代码的缓存文件
STOCK_CODE_CACHE = "stock_code_cache.json"

# 请求头配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://finance.sina.com.cn/'
}

def load_stock_code_cache():
    """加载股票名称到代码的缓存"""
    try:
        if os.path.exists(STOCK_CODE_CACHE):
            with open(STOCK_CODE_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"加载股票代码缓存失败: {e}")
        return {}

def save_stock_code_cache(cache):
    """保存股票名称到代码的缓存"""
    try:
        with open(STOCK_CODE_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存股票代码缓存失败: {e}")

def load_existing_results():
    """加载已有的分析结果"""
    try:
        if os.path.exists(OUTPUT_EXCEL):
            existing_df = pd.read_excel(OUTPUT_EXCEL)
            print(f"已加载现有结果文件中的 {len(existing_df)} 条记录")
            return existing_df
        else:
            print("未找到现有结果文件，将创建新文件")
            return pd.DataFrame()
    except Exception as e:
        print(f"加载现有结果文件失败: {e}")
        return pd.DataFrame()

def is_stock_processed(code, existing_df):
    """检查股票是否已经被处理过"""
    if existing_df.empty:
        return False
    
    # 清理代码格式以便比较
    clean_code = str(code).replace('.BJ', '').strip()
    
    # 检查证券代码列中是否存在该股票
    if '证券代码' in existing_df.columns:
        existing_codes = existing_df['证券代码'].astype(str).str.replace('.BJ', '').str.strip()
        return clean_code in existing_codes.values
    
    return False

def save_results_with_retry(results_df, max_retries=3):
    """带重试机制的结果保存函数，并优化Excel格式"""
    for attempt in range(max_retries):
        try:
            # 指定列顺序
            columns = [
                '证券代码', '证券简称', '公告日期',
                '开始日期', '结束日期',
                '区间涨跌幅', '期间最高涨幅', '指数涨跌幅', '相对涨跌幅'
            ]
            # 只保留需要的列
            results_df = results_df[columns]

            # 保留两位小数
            float_cols = ['区间涨跌幅', '期间最高涨幅', '指数涨跌幅', '相对涨跌幅']
            for col in float_cols:
                if col in results_df.columns:
                    results_df[col] = results_df[col].map(lambda x: round(x, 2) if pd.notnull(x) else x)

            # 按相对涨跌幅排序
            sorted_df = results_df.sort_values('相对涨跌幅', ascending=False)

            # 如果文件被占用，尝试使用临时文件名
            output_file = OUTPUT_EXCEL
            if attempt > 0:
                base_name = OUTPUT_EXCEL.replace('.xlsx', '')
                output_file = f"{base_name}_temp_{attempt}.xlsx"

            # 保存为Excel
            sorted_df.to_excel(output_file, index=False)

            # 设置列宽和日期格式
            wb = openpyxl.load_workbook(output_file)
            ws = wb.active
            if ws is not None:
                col_widths = [12, 16, 12, 12, 12, 12, 14, 12, 12]
                for i, width in enumerate(col_widths, 1):
                    ws.column_dimensions[get_column_letter(i)].width = width
                # 设置日期格式
                for col in ['公告日期', '开始日期', '结束日期']:
                    if col in columns:
                        idx = columns.index(col) + 1
                        for cell in ws[get_column_letter(idx)]:
                            cell.number_format = 'yyyy-mm-dd'
                wb.save(output_file)
            else:
                print("警告：未能获取到有效的工作表，无法设置列宽")

            if attempt > 0:
                print(f"原文件被占用，已保存为: {output_file}")
            return True

        except PermissionError as e:
            print(f"文件保存失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("请关闭Excel文件后，程序将在3秒后重试...")
                time.sleep(3)
            else:
                print("多次尝试失败，请手动关闭Excel文件后重新运行程序")
                return False
        except Exception as e:
            print(f"保存文件时发生其他错误: {e}")
            return False

    return False

def clean_stock_code(code):
    """清理股票代码格式"""
    if isinstance(code, str):
        # 去除.BJ后缀
        code = code.replace('.BJ', '').replace('.bj', '')
        # 去除可能的空格
        code = code.strip()
    return str(code)

def search_stock_by_name(stock_name: str, cache: Dict[str, str]) -> Optional[str]:
    """通过股票名称搜索获取股票代码"""
    # 先检查缓存
    if stock_name in cache:
        print(f"从缓存获取 {stock_name} 的代码: {cache[stock_name]}")
        return cache[stock_name]
    
    try:
        # 使用新浪财经的搜索API
        search_url = "https://suggest3.sinajs.cn/suggest/type=11,12,13,14,15&key="
        encoded_name = urllib.parse.quote(stock_name)
        
        response = requests.get(f"{search_url}{encoded_name}", headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # 解析搜索结果
        content = response.text
        if 'var suggestvalue="' in content:
            suggest_data = content.split('var suggestvalue="')[1].split('";')[0]
            
            if suggest_data:
                items = suggest_data.split(';')
                for item in items:
                    if item:
                        parts = item.split(',')
                        if len(parts) >= 6:
                            code = parts[3]  # 股票代码
                            name = parts[4]  # 股票名称
                            market = parts[1]  # 市场代码
                            
                            # 检查是否是北交所股票（市场代码为bj或代码以8开头）
                            if (market == 'bj' or code.startswith('8')) and stock_name in name:
                                print(f"搜索到 {stock_name} 的代码: {code}")
                                # 保存到缓存
                                cache[stock_name] = code
                                save_stock_code_cache(cache)
                                return code
        
        # 如果新浪API失败，尝试其他方法
        print(f"新浪搜索未找到 {stock_name}，尝试其他方法...")
        
        # 备用方案：使用东方财富搜索API
        backup_url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            'input': stock_name,
            'type': '14',
            'token': 'D43BF722C8E33BDC906FB84D85E326E8',
            'count': '5'
        }
        
        response = requests.get(backup_url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('QuotationCodeTable') and data['QuotationCodeTable'].get('Data'):
                for item in data['QuotationCodeTable']['Data']:
                    code = item.get('Code', '')
                    name = item.get('Name', '')
                    market_type = item.get('MktNum', '')
                    
                    # 北交所的市场代码通常是116
                    if (market_type == '116' or code.startswith('8')) and stock_name in name:
                        print(f"通过东方财富搜索到 {stock_name} 的代码: {code}")
                        cache[stock_name] = code
                        save_stock_code_cache(cache)
                        return code
        
        print(f"未找到股票 {stock_name} 的代码")
        return None
        
    except Exception as e:
        print(f"搜索股票 {stock_name} 时出错: {e}")
        return None

def get_stock_info_by_name(stock_name: str) -> Tuple[Optional[str], Optional[str]]:
    """通过股票名称获取股票代码和完整名称"""
    cache = load_stock_code_cache()
    
    # 清理股票名称（去除可能的前缀、后缀）
    clean_name = stock_name.strip()
    
    # 尝试直接搜索
    code = search_stock_by_name(clean_name, cache)
    if code:
        return code, clean_name
    
    # 如果直接搜索失败，尝试去除常见的后缀
    suffixes_to_remove = ['股份', '有限公司', '科技', '技术', '实业', '集团']
    for suffix in suffixes_to_remove:
        if clean_name.endswith(suffix):
            short_name = clean_name.replace(suffix, '').strip()
            code = search_stock_by_name(short_name, cache)
            if code:
                return code, clean_name
    
    return None, clean_name

def get_trading_date(date_str, offset=30):
    """获取指定日期后的交易日期范围"""
    try:
        # 简化逻辑：直接计算日期范围
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        trading_start = start_date
        trading_end = start_date + timedelta(days=offset)
        
        # 确保是工作日（简单过滤周末）
        while trading_start.weekday() >= 5:  # 0-6，5和6是周末
            trading_start += timedelta(days=1)
        
        while trading_end.weekday() >= 5:
            trading_end -= timedelta(days=1)
        
        return trading_start.strftime('%Y-%m-%d'), trading_end.strftime('%Y-%m-%d')
            
    except Exception as e:
        print(f"获取交易日期范围失败: {e}")
        # 返回简单的日期范围
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = start_date + timedelta(days=offset)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def calculate_return(code, start_date, end_date):
    """计算指定股票在给定时间范围内的涨跌幅和最高涨幅，使用新浪财经API"""
    try:
        # 添加延时
        time.sleep(0.5)
        
        # 处理北交所股票代码格式
        if code.endswith('.BJ'):
            code = code.replace('.BJ', '')
        
        # 新浪财经API - 北交所股票
        url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_k_240_1=/CN_MarketDataService.getKLineData"
        
        params = {
            'symbol': f'bj{code}',  # 北交所股票使用bj前缀
            'scale': '240',  # 日K线
            'ma': 'no',
            'datalen': '500'  # 获取足够的数据
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # 解析JSONP响应
        content = response.text
        json_match = re.search(r'var.*?=\((.*?)\);?$', content)
        
        if not json_match:
            print(f"无法解析股票 {code} 的响应数据")
            return None, None
            
        data = json.loads(json_match.group(1))
        
        if not data or len(data) == 0:
            print(f"股票 {code} 返回空数据")
            return None, None
        
        # 转换为DataFrame
        df_data = []
        for item in data:
            if isinstance(item, dict):
                df_data.append({
                    'date': item.get('day', ''),
                    'close': float(item.get('close', 0)),
                    'high': float(item.get('high', 0))  # 添加最高价
                })
        
        if not df_data:
            return None, None
            
        df = pd.DataFrame(df_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 过滤日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
        df = df[mask].sort_values('date')
        
        if df.empty or len(df) < 2:
            print(f"股票 {code} 在指定日期范围内无足够数据")
            return None, None
        
        # 计算期间涨跌幅（开始到结束）
        first_close = df.iloc[0]['close']
        last_close = df.iloc[-1]['close']
        period_return = (last_close - first_close) / first_close * 100
        
        # 计算期间最高涨幅（从第一天收盘价到期间内任意一天的最高价）
        period_max_high = df['high'].max()
        max_return = (period_max_high - first_close) / first_close * 100
        
        return period_return, max_return
        
    except Exception as e:
        print(f"获取{code}行情数据失败: {e}")
        return None, None

def calculate_index_return(start_date, end_date):
    """计算北证50指数在给定时间范围内的涨跌幅，使用新浪财经API"""
    try:
        # 添加延时
        time.sleep(0.5)
        
        # 新浪财经API - 北证50指数
        url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_k_240_1=/CN_MarketDataService.getKLineData"
        
        params = {
            'symbol': f'bj{INDEX_CODE}',  # 北证50指数
            'scale': '240',  # 日K线
            'ma': 'no',
            'datalen': '500'
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # 解析JSONP响应
        content = response.text
        json_match = re.search(r'var.*?=\((.*?)\);?$', content)
        
        if not json_match:
            print(f"无法解析北证50指数的响应数据")
            return None
            
        data = json.loads(json_match.group(1))
        
        if not data or len(data) == 0:
            print(f"北证50指数返回空数据")
            return None
        
        # 转换为DataFrame
        df_data = []
        for item in data:
            if isinstance(item, dict):
                df_data.append({
                    'date': item.get('day', ''),
                    'close': float(item.get('close', 0))
                })
        
        if not df_data:
            return None
            
        df = pd.DataFrame(df_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 过滤日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
        df = df[mask].sort_values('date')
        
        if df.empty or len(df) < 2:
            print(f"北证50指数在 {start_date} 至 {end_date} 期间无足够数据")
            return None
        
        # 计算指数涨跌幅
        first_close = df.iloc[0]['close']
        last_close = df.iloc[-1]['close']
        return (last_close - first_close) / first_close * 100
        
    except Exception as e:
        print(f"获取指数行情数据失败: {e}")
        return None

def analyze_performance():
    """分析股票相对于指数的表现"""
    # 检查并读取输入文件
    if not os.path.exists(INPUT_EXCEL):
        print(f"未找到输入文件: {INPUT_EXCEL}")
        return
    
    # 读取Excel文件
    df = pd.read_excel(INPUT_EXCEL)
    
    # 验证必需的列是否存在
    required_columns = ['证券简称', '公告日期']
    if '证券代码' in df.columns:
        required_columns.append('证券代码')
    
    missing_columns = [col for col in ['证券简称', '公告日期'] if col not in df.columns]
    if missing_columns:
        print(f"Excel文件缺少必需的列: {missing_columns}")
        print(f"当前文件包含的列: {list(df.columns)}")
        return
    
    # 加载已有结果
    existing_results_df = load_existing_results()
    
    # 存储所有结果（包括已有的和新处理的）
    all_results: List[dict] = []
    
    # 如果有已有结果，加入到all_results中
    if not existing_results_df.empty:
        all_results = existing_results_df.to_dict('records')
    
    # 遍历每只股票进行分析
    total_stocks = len(df)
    processed_count = 0
    skipped_count = 0
    
    for current_idx, (_, row) in enumerate(df.iterrows(), 1):
        # 获取股票基本信息
        name = row['证券简称']
        announce_date = row['公告日期']
        
        # 优先使用证券代码（如果存在），否则通过名称搜索
        if '证券代码' in df.columns and pd.notna(row['证券代码']):
            code = clean_stock_code(row['证券代码'])
            print(f"使用提供的证券代码: {code} (原始: {row['证券代码']})")
        else:
            # 通过股票名称获取代码
            print(f"正在搜索股票代码: {name}")
            code, full_name = get_stock_info_by_name(name)
            if not code:
                print(f"警告: 无法找到股票 {name} 的代码，跳过")
                continue
            name = full_name  # 使用完整名称
        
        # 检查股票是否已经处理过
        if is_stock_processed(code, existing_results_df):
            print(f"跳过已处理的股票: {code} {name}")
            skipped_count += 1
            continue
        
        print(f"\n{'-'*60}")
        print(f"进度: [{current_idx}/{total_stocks}] (已处理: {processed_count}, 已跳过: {skipped_count})")
        print(f"股票信息: {code} {name}")
        print(f"公告日期: {announce_date}")
        print(f"{'-'*60}")
        
        try:
            # 确保日期格式正确
            if isinstance(announce_date, str):
                announce_date_str = announce_date
            else:
                announce_date_str = announce_date.strftime('%Y-%m-%d')
            
            # 获取交易日期范围
            start_date, end_date = get_trading_date(announce_date_str)
            if start_date is None or end_date is None:
                print(f"警告: 无法获取 {code} 的交易日期范围")
                continue
            
            print(f"计算区间: {start_date} 至 {end_date}")
            
            # 计算个股涨跌幅和最高涨幅
            stock_return, max_return = calculate_return(code, start_date, end_date)
            if stock_return is None or max_return is None:
                print(f"警告: 无法获取 {code} 的股票行情数据")
                continue
            
            print(f"个股涨跌幅: {round(stock_return, 2)}%")
            print(f"期间最高涨幅: {round(max_return, 2)}%")
            
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
            result = {
                '证券代码': code,
                '证券简称': name,
                '公告日期': announce_date_str,
                '区间涨跌幅': round(stock_return, 2),
                '期间最高涨幅': round(max_return, 2),
                '指数涨跌幅': round(index_return, 2),
                '相对涨跌幅': round(relative_return, 2),
                '开始日期': start_date,
                '结束日期': end_date
            }
            
            # 添加到结果列表
            all_results.append(result)
            processed_count += 1
            
            # 实时保存结果到Excel
            results_df = pd.DataFrame(all_results)
            if not save_results_with_retry(results_df):
                print(f"警告: 无法保存文件，但数据已在内存中保留")
            
            print(f"数据已处理: {code} {name}")
            
        except Exception as e:
            print(f"处理 {name} 时发生错误: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            continue
    
    print(f"\n{'-'*60}")
    print(f"处理完成!")
    print(f"总股票数: {total_stocks}")
    print(f"新处理股票数: {processed_count}")
    print(f"跳过已处理股票数: {skipped_count}")
    print(f"最终结果总数: {len(all_results)}")
    
    # 最终排序并保存
    try:
        final_df = pd.DataFrame(all_results)
        if not save_results_with_retry(final_df):
            print("最终保存失败，请检查文件权限")
        else:
            print("最终结果已按相对涨跌幅排序完成")
    except Exception as e:
        print(f"最终排序保存时发生错误: {e}")

# 程序入口点
if __name__ == "__main__":
    analyze_performance()