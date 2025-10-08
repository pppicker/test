import akshare as ak
import time
import pandas as pd
from datetime import datetime, timedelta

def test_stock_data_api(stock_code: str = "836433.BJ", days: int = 30) -> None:
    """测试股票日线数据获取接口"""
    print(f"\n{'-'*60}")
    print(f"开始测试股票 {stock_code} 的数据获取")
    
    try:
        # 计算日期范围并直接转换为8位字符串格式
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        print(f"测试区间: {start_date} 至 {end_date}")
        
        # 添加延时
        time.sleep(0.5)  # 增加延时到0.5秒
        
        # 获取股票日线数据
        print(f"正在获取 {stock_code} 的数据...")
        df = ak.stock_zh_a_hist(
            symbol=stock_code.replace('.BJ', ''),  # 移除后缀
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        # 检查数据是否为空
        if df.empty:
            print(f"警告: 未获取到股票 {stock_code} 的数据")
            return
        
        # 打印数据信息
        print(f"\n获取到 {len(df)} 条数据")
        print("\n数据示例:")
        print(df.head())
        print("\n数据列:")
        print(df.columns.tolist())
        
        # 检查关键字段
        required_columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"\n警告: 缺少以下关键字段: {missing_columns}")
        else:
            print("\n所有关键字段都存在")
        
        print("\n数据类型:")
        print(df.dtypes)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
    
    print(f"\n{'-'*60}")

def main():
    """主函数：运行测试用例"""
    # 测试样例股票
    test_cases = [
        "430017",  # 正常股票
        "603777.BJ",  # 带后缀的股票代码
        "000000"   # 无效股票代码
    ]
    
    for stock_code in test_cases:
        test_stock_data_api(stock_code)
        time.sleep(1)  # 测试间隔增加到1秒

if __name__ == "__main__":
    main()