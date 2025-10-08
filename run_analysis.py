import os
import subprocess
import sys

def run_script(script_name):
    """执行指定的Python脚本"""
    print(f"\n开始执行 {script_name}...")
    
    try:
        # 使用 Python 解释器执行脚本
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            text=True,
            capture_output=True
        )
        
        # 打印脚本的输出
        if result.stdout:
            print(result.stdout)
            
        print(f"{script_name} 执行完成\n")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"执行 {script_name} 时发生错误:")
        print(f"错误代码: {e.returncode}")
        if e.stdout:
            print("输出信息:")
            print(e.stdout)
        if e.stderr:
            print("错误信息:")
            print(e.stderr)
        return False

def main():
    """主函数：按顺序执行脚本"""
    # 要执行的脚本列表
    scripts = [
        "playwright_fetch_bz50_announcements.py",
        "analyze_bz50_performance.py"
    ]
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 切换到脚本所在目录
    os.chdir(current_dir)
    
    # 检查所有脚本是否存在
    missing_files = [script for script in scripts if not os.path.exists(script)]
    if missing_files:
        print("错误: 以下脚本文件不存在:")
        for file in missing_files:
            print(f"- {file}")
            print(f"  预期路径: {os.path.join(current_dir, file)}")
        return
    
    # 依次执行每个脚本
    for script in scripts:
        success = run_script(script)
        if not success:
            print(f"执行 {script} 失败，终止后续操作")
            return
            
    print("所有脚本执行完成!")

if __name__ == "__main__":
    main()