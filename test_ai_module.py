#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI模块自动化测试脚本
用于验证AI模块的各项功能是否正常工作
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8083")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "admin123")
TEST_BOOK_IDS = [42, 52, 51, 45, 36, 37, 38, 39, 40, 41]  # 测试书籍ID列表

# 测试结果存储
test_results: List[Dict] = []


class Colors:
    """终端颜色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印测试标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_test(test_name: str, status: str, message: str = ""):
    """打印测试结果"""
    status_color = Colors.GREEN if status == "PASS" else Colors.RED
    status_symbol = "✓" if status == "PASS" else "✗"
    print(f"{status_color}{status_symbol} {test_name}{Colors.END}", end="")
    if message:
        print(f" - {message}")
    else:
        print()
    
    test_results.append({
        "test_name": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })


def get_session() -> requests.Session:
    """获取登录后的session"""
    session = requests.Session()
    login_url = f"{BASE_URL}/login"
    
    # 获取CSRF token
    response = session.get(login_url)
    if response.status_code != 200:
        print(f"{Colors.RED}无法访问登录页面: {response.status_code}{Colors.END}")
        sys.exit(1)
    
    # 尝试登录（需要根据实际登录方式调整）
    # 这里假设使用表单登录
    login_data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    }
    
    response = session.post(login_url, data=login_data, allow_redirects=False)
    
    if response.status_code not in [200, 302]:
        print(f"{Colors.YELLOW}警告: 登录可能失败，状态码: {response.status_code}{Colors.END}")
        print(f"{Colors.YELLOW}请手动设置session cookie或调整登录逻辑{Colors.END}")
    
    return session


def test_api_endpoint(session: requests.Session, endpoint: str, book_id: int, 
                     expected_status: int = 200) -> Tuple[bool, str, Optional[Dict]]:
    """测试API端点"""
    url = f"{BASE_URL}{endpoint.format(book_id=book_id)}"
    
    try:
        start_time = time.time()
        response = session.get(url, timeout=45)
        elapsed_time = time.time() - start_time
        
        if response.status_code == expected_status:
            try:
                data = response.json()
                return True, f"状态码: {response.status_code}, 响应时间: {elapsed_time:.2f}秒", data
            except ValueError:
                return True, f"状态码: {response.status_code}, 响应时间: {elapsed_time:.2f}秒, 非JSON响应", None
        else:
            return False, f"状态码: {response.status_code}, 预期: {expected_status}", None
            
    except requests.exceptions.Timeout:
        return False, "请求超时（>45秒）", None
    except requests.exceptions.RequestException as e:
        return False, f"请求异常: {str(e)}", None


def test_book_summary_api(session: requests.Session, book_id: int) -> bool:
    """测试书籍摘要API"""
    endpoint = "/ajax/ai/book_summary/{book_id}"
    success, message, data = test_api_endpoint(session, endpoint, book_id)
    
    if success:
        if data and "content" in data:
            content_length = len(data["content"])
            print_test(
                f"TC-001: 书籍摘要API (Book ID: {book_id})",
                "PASS",
                f"{message}, 内容长度: {content_length}字符"
            )
            return True
        else:
            print_test(
                f"TC-001: 书籍摘要API (Book ID: {book_id})",
                "FAIL",
                f"{message}, 但响应格式不正确"
            )
            return False
    else:
        print_test(
            f"TC-001: 书籍摘要API (Book ID: {book_id})",
            "FAIL",
            message
        )
        return False


def test_book_recommendations_api(session: requests.Session, book_id: int) -> bool:
    """测试书籍推荐API"""
    endpoint = "/ajax/ai/book_recommendations/{book_id}"
    success, message, data = test_api_endpoint(session, endpoint, book_id)
    
    if success:
        if data and "content" in data:
            content_length = len(data["content"])
            print_test(
                f"TC-003: 书籍推荐API (Book ID: {book_id})",
                "PASS",
                f"{message}, 内容长度: {content_length}字符"
            )
            return True
        else:
            print_test(
                f"TC-003: 书籍推荐API (Book ID: {book_id})",
                "FAIL",
                f"{message}, 但响应格式不正确"
            )
            return False
    else:
        print_test(
            f"TC-003: 书籍推荐API (Book ID: {book_id})",
            "FAIL",
            message
        )
        return False


def test_error_scenarios(session: requests.Session):
    """测试错误场景"""
    print_header("错误场景测试")
    
    # 测试不存在的书籍
    endpoint = "/ajax/ai/book_summary/{book_id}"
    success, message, _ = test_api_endpoint(session, endpoint, 99999, expected_status=404)
    print_test(
        "TC-004: 不存在的书籍ID",
        "PASS" if not success else "FAIL",
        message
    )
    
    # 测试无效的书籍ID
    try:
        url = f"{BASE_URL}/ajax/ai/book_summary/abc"
        response = session.get(url, timeout=10)
        print_test(
            "TC-004: 无效的书籍ID格式",
            "PASS" if response.status_code == 404 else "FAIL",
            f"状态码: {response.status_code}"
        )
    except Exception as e:
        print_test(
            "TC-004: 无效的书籍ID格式",
            "FAIL",
            f"异常: {str(e)}"
        )


def test_performance(session: requests.Session, book_id: int):
    """性能测试"""
    print_header("性能测试")
    
    endpoint = "/ajax/ai/book_summary/{book_id}"
    response_times = []
    
    print(f"{Colors.YELLOW}正在进行5次性能测试...{Colors.END}")
    for i in range(5):
        success, message, _ = test_api_endpoint(session, endpoint, book_id)
        if success:
            # 从message中提取响应时间
            import re
            match = re.search(r'响应时间: ([\d.]+)秒', message)
            if match:
                response_times.append(float(match.group(1)))
        time.sleep(2)  # 避免请求过快
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        print_test(
            "TC-014: API响应时间",
            "PASS" if avg_time < 30 else "FAIL",
            f"平均: {avg_time:.2f}秒, 最大: {max_time:.2f}秒, 最小: {min_time:.2f}秒"
        )
    else:
        print_test(
            "TC-014: API响应时间",
            "FAIL",
            "无法获取响应时间数据"
        )


def generate_report():
    """生成测试报告"""
    print_header("测试报告汇总")
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{Colors.BOLD}测试统计:{Colors.END}")
    print(f"  总测试数: {total}")
    print(f"  通过: {Colors.GREEN}{passed}{Colors.END}")
    print(f"  失败: {Colors.RED}{failed}{Colors.END}")
    print(f"  通过率: {pass_rate:.1f}%")
    
    print(f"\n{Colors.BOLD}详细结果:{Colors.END}")
    for result in test_results:
        status_color = Colors.GREEN if result["status"] == "PASS" else Colors.RED
        print(f"  {status_color}{result['status']}{Colors.END} - {result['test_name']}")
        if result['message']:
            print(f"    {result['message']}")
    
    # 保存JSON报告
    report_file = f"ai_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": pass_rate
            },
            "results": test_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{Colors.BLUE}详细报告已保存到: {report_file}{Colors.END}")
    
    return pass_rate >= 80  # 80%通过率视为测试通过


def main():
    """主测试函数"""
    print_header("AI模块自动化测试")
    
    print(f"{Colors.BLUE}测试配置:{Colors.END}")
    print(f"  测试URL: {BASE_URL}")
    print(f"  测试用户: {TEST_USERNAME}")
    print(f"  测试书籍ID: {TEST_BOOK_IDS[:3]}...")
    
    # 检查环境变量
    if not os.getenv("DEEPSEEK_API_KEY"):
        print(f"\n{Colors.YELLOW}警告: DEEPSEEK_API_KEY 环境变量未设置{Colors.END}")
        print(f"{Colors.YELLOW}某些测试可能会失败{Colors.END}\n")
    
    # 获取session
    print(f"\n{Colors.BLUE}正在获取登录session...{Colors.END}")
    session = get_session()
    
    # 功能测试
    print_header("功能测试")
    
    # 测试第一个书籍的摘要和推荐
    if TEST_BOOK_IDS:
        test_book_id = TEST_BOOK_IDS[0]
        test_book_summary_api(session, test_book_id)
        time.sleep(2)  # 避免请求过快
        test_book_recommendations_api(session, test_book_id)
    
    # 测试多个书籍
    print(f"\n{Colors.YELLOW}测试多个书籍的摘要生成...{Colors.END}")
    for book_id in TEST_BOOK_IDS[:3]:  # 只测试前3个
        test_book_summary_api(session, book_id)
        time.sleep(2)
    
    # 错误场景测试
    test_error_scenarios(session)
    
    # 性能测试
    if TEST_BOOK_IDS:
        test_performance(session, TEST_BOOK_IDS[0])
    
    # 生成报告
    success = generate_report()
    
    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 测试通过！{Colors.END}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 测试未完全通过，请检查失败项{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()

