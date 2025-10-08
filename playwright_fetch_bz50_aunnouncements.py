# -*- coding: utf-8 -*-                                                # 指定源码文件编码为 UTF-8，避免中文注释乱码

from playwright.sync_api import sync_playwright                         # 引入 Playwright 同步 API，用于驱动（无头）浏览器
import pandas as pd                                                     # 用于读取与解析 Excel
import re, os, json                                                     # re: 正则表达式；os: 文件/路径；json: 序列化结果
from datetime import datetime, timedelta                                # 用于处理日期与“最近两年”筛选
from urllib.parse import urljoin, urlparse                              # urljoin: 拼相对链接；urlparse: 解析 URL 路径
import requests                                                         # 作为下载兜底（附带 Cookie/UA/Referer），降低 403 概率

# ---------------------------- 基本配置 ----------------------------

BASE_URL = "https://www.bse.cn/market_data/bse_indices/bse_bz50.html"  # 北证50页面（内容由 JS 动态渲染）
TARGET_TITLE = "关于北证50（899050）样本股定期调整的公告"                   # 只匹配标题包含这段文字的资讯条目
DOWNLOAD_DIR = "bz50_downloads"                                         # 附件下载保存目录
OUTPUT_JSON = "stocks_info.json"                                        # 结果 JSON 文件名
ONLY_LAST_YEARS = 0                                                     # 可选：只保留最近 N 年的公告（在解析出日期后再过滤）
os.makedirs(DOWNLOAD_DIR, exist_ok=True)                                # 若目录不存在则创建

# ---------------------------- 工具函数 ----------------------------

def parse_date(text: str):
    """
    从任意文本中尽量解析出公告日期，返回 'YYYY-MM-DD' 字符串；解析失败返回 None。
    支持三类常见格式：
    1) 2025-09-09 / 2025/9/9 / 2025.9.9
    2) 2025年9月9日
    3) 20250909 （纯 8 位数字）
    """
    m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)         # 匹配连字符/斜杠/点分隔的日期
    if m:                                                               # 若匹配成功
        y, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))  # 取出年、月、日
        try:
            return f"{y:04d}-{mm:02d}-{dd:02d}"                         # 格式化为 YYYY-MM-DD
        except ValueError:
            pass                                                        # 非法日期则忽略，继续尝试其他格式

    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)              # 匹配中文日期“YYYY年M月D日”
    if m:                                                               # 若匹配成功
        y, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))  # 取出年、月、日
        try:
            return f"{y:04d}-{mm:02d}-{dd:02d}"                         # 格式化为 YYYY-MM-DD
        except ValueError:
            pass                                                        # 非法日期则忽略

    m = re.search(r"\b(\d{8})\b", text)                                 # 匹配纯 8 位数字的日期（如 20250909）
    if m:                                                               # 若匹配成功
        s = m.group(1)                                                  # 取出 8 位字符串
        try:
            return datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")  # 按 %Y%m%d 解析并格式化
        except ValueError:
            pass                                                        # 非法日期则忽略

    return None                                                         # 所有格式都不匹配则返回 None

def normalize_code(code):
    """
    将证券代码标准化：
    - 若为 6 位纯数字（Excel 易读成数字/浮点），自动补 '.BJ'
    - 若已带 .BJ/.SH/.SZ 后缀，统一转为大写
    - 其他情况原样返回
    """
    s = str(code).strip()                                               # 转字符串并去除首尾空格
    s = re.sub(r"\.0+$", "", s)                                         # Excel 读数值时可能带小数（如 '839493.0'），去掉
    if re.fullmatch(r"\d{6}", s):                                       # 如果是 6 位纯数字
        return s + ".BJ"                                                # 视为北交所代码，加 '.BJ'
    if re.fullmatch(r"\d{6}\.(BJ|SH|SZ)", s, flags=re.I):               # 若已带市场后缀
        return s.upper()                                                # 统一转成大写
    return s                                                            # 其他情况返回原值

# -------------------- 独立的 Excel 解析方法（每行注释） --------------------

def parse_excel_file(path: str):
    """
    从固定区域读取 Excel 内容：
    - 证券代码：第4列，第4-53行
    - 证券简称：第5列，第4-53行
    - 公告日期：从文件名提取前8位数字作为日期
    返回格式：[{'code': '839493.BJ', 'name': '并行科技', 'announce_date': '2025-09-09'}, ...]
    """
    out_rows = []
    try:
        # 读取 Excel，无表头，所有列按字符串处理
        df = pd.read_excel(
            path, 
            sheet_name=0,  # 默认第一个 sheet
            header=None,   # 无表头
            dtype=str      # 所有列按字符串处理
        )
        
        # 固定取第4列(索引3)作为代码列，第5列(索引4)作为名称列
        # 行范围从第4行到第53行(索引3到52)
        code_series = df.iloc[3:53, 3]    # 第4列，第4-53行
        name_series = df.iloc[3:53, 4]    # 第5列，第4-53行
        
        # 从文件名提取日期（取前8位数字）
        fname = os.path.basename(path)
        date_match = re.search(r'\d{8}', fname)
        if date_match:
            announce_date = datetime.strptime(
                date_match.group(), '%Y%m%d'
            ).strftime('%Y-%m-%d')
        else:
            announce_date = ""
            
        # 遍历处理每一行
        for raw_code, raw_name in zip(code_series, name_series):
            code = normalize_code(raw_code)
            name = "" if raw_name is None else str(raw_name).strip()
            
            # 跳过空值
            if not code or not name:
                continue
                
            out_rows.append({
                "code": code,
                "name": name,
                "announce_date": announce_date
            })
            
    except Exception as e:
        print(f"[WARN] 解析Excel文件失败 {path}: {e}")
        return []
        
    return out_rows

def fetch_detail_urls(context):
    page = context.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#foot_ul li, .mw-newlist li", timeout=30000)
    links = page.locator("a", has_text=TARGET_TITLE)
    detail_urls = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        if href:
            detail_urls.append(urljoin(BASE_URL, href))
    page.close()
    return detail_urls

def download_and_parse_excels(context, detail_urls):
    stocks_info = []
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in context.cookies()])
    ua = context.pages[0].evaluate("() => navigator.userAgent") if context.pages else ""
    common_headers = {
        "User-Agent": ua,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    for du in detail_urls:
        dp = context.new_page()
        dp.goto(du, wait_until="domcontentloaded")
        dp.wait_for_timeout(1000)
        a_tags = dp.locator("a[href$='.xls'], a[href$='.xlsx']")
        for j in range(a_tags.count()):
            xhref = a_tags.nth(j).get_attribute("href")
            if not xhref:
                continue
            xurl = urljoin(du, xhref)
            fname = os.path.basename(urlparse(xurl).path)
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            downloaded = False
            if not os.path.exists(fpath):
                try:
                    with dp.expect_download() as dl_info:
                        a_tags.nth(j).click()
                    download = dl_info.value
                    download.save_as(fpath)
                    downloaded = True
                except Exception as e1:
                    try:
                        headers = dict(common_headers)
                        headers["Referer"] = du
                        headers["Cookie"] = cookie_str
                        r = requests.get(xurl, headers=headers, timeout=30)
                        r.raise_for_status()
                        with open(fpath, "wb") as f:
                            f.write(r.content)
                        downloaded = True
                    except Exception as e2:
                        print(f"[WARN] 附件下载失败：{xurl}\n  - playwright err: {e1}\n  - requests err: {e2}")
                        continue
            try:
                rows = parse_excel_file(fpath)
                stocks_info.extend(rows)
            except Exception as pe:
                print(f"[WARN] 解析失败 {fpath}: {pe}")
        dp.close()
    return stocks_info

def filter_by_years(stocks_info, only_last_years):
    if only_last_years and only_last_years > 0:
        cutoff = datetime.today() - timedelta(days=365 * only_last_years)
        filtered = []
        for r in stocks_info:
            try:
                ad = datetime.strptime(r["announce_date"], "%Y-%m-%d")
                if ad >= cutoff:
                    filtered.append(r)
            except Exception:
                filtered.append(r)
        return filtered
    return stocks_info

def print_stocks_info(stocks_info):
    print("stocks_info = [")
    for r in stocks_info:
        print(f"    {{\"code\": \"{r['code']}\", "
              f"\"name\": \"{r['name']}\", "
              f"\"announce_date\": \"{r['announce_date']}\"}},")
    print("]  # 共", len(stocks_info), "条")

def save_to_excel(stocks_info, output_excel="stocks_info.xlsx"):
    try:
        df = pd.DataFrame(stocks_info)
        df = df[["code", "name", "announce_date"]]
        df.columns = ["证券代码", "证券简称", "公告日期"]
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='北证50成分股')
            worksheet = writer.sheets['北证50成分股']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
        print(f"\n结果已保存到 Excel 文件：{output_excel}")
    except Exception as e:
        print(f"[ERROR] 写入 Excel 失败: {e}")

# ---------------------------- 主流程 ----------------------------

def main():
    stocks_info = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1366, "height": 850},
            color_scheme="light",
            accept_downloads=True,
        )
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        detail_urls = fetch_detail_urls(context)
        stocks_info = download_and_parse_excels(context, detail_urls)
        browser.close()

    stocks_info = filter_by_years(stocks_info, ONLY_LAST_YEARS)
    print_stocks_info(stocks_info)
    save_to_excel(stocks_info)

# ---------------------------- 程序入口 ----------------------------

if __name__ == "__main__":                                               # 如果脚本被直接运行
    main()                                                          # 执行主流程
