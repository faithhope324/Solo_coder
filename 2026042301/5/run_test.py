"""运行测试脚本"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, 'test_bug_fixes.py'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)

print("STDOUT:")
print(result.stdout if result.stdout else "(无输出)")
print("\nSTDERR:")
print(result.stderr if result.stderr else "(无输出)")
print(f"\n返回码: {result.returncode}")
