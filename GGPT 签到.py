import re

import requests
import time
import urllib.parse
from http.cookies import SimpleCookie
import random
"""
用于 gamegamePT 签到保号
用法：在 main 函数中输入字符串格式 Cookies
"""

def cookie_str_to_dict(cookie_str):
    """将cookie字符串转换为字典"""
    cookie = SimpleCookie()
    cookie.load(cookie_str)
    return {key: morsel.value for key, morsel in cookie.items()}


def create_session_with_retry(cookies_str, max_retries=3):
    """创建带有重试机制的session"""
    session = requests.Session()

    # 设置cookie
    cookies_dict = cookie_str_to_dict(cookies_str)
    session.cookies.update(cookies_dict)

    # 设置默认请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    session.headers.update(headers)

    # 添加请求适配器，设置连接池和重试
    from requests.adapters import HTTPAdapter
    # from requests.packages.urllib3.util.retry import Retry
    from urllib3.util import Retry

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session


def safe_request(session, method, url, **kwargs):
    """安全的请求函数，带延迟和异常处理"""
    # 添加随机延迟，避免请求过于频繁
    time.sleep(random.uniform(1, 3))

    try:
        response = session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        # 如果是连接重置，可能是服务器限制了并发
        if "Connection reset by peer" in str(e):
            print("检测到连接重置，增加延迟并重试...")
            time.sleep(5)  # 等待更长时间
            # 可以在这里添加重试逻辑
        raise
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        raise

def parse_sign_in_info(text):
    """
    解析签到信息（简洁实用版）

    参数:
    text (str): HTML响应文本

    返回:
    dict: 签到信息
    """
    if not text:
        return {}

    # 提取数据
    sign_count = re.search(r'第\s*<b>\s*(\d+)\s*</b>\s*次签到', text)
    continuous = re.search(r'连续签到\s*<b>\s*(\d+)\s*</b>\s*天', text)
    magic_earned = re.search(r'获得\s*<b>\s*(\d+)\s*</b>\s*个魔力值', text)
    total_magic = re.search(r'魔力值\s*</font>\[.*?\]\s*:\s*([\d,]+\.\d+)', text)
    QD_card = re.search(r'你目前拥有补签卡\s*<b>\s*(\d+)\s*</b>\s*张', text)
    rank_match = re.search(r'今日签到排名：\s*<b>\s*(\d+)\s*</b>\s*/\s*<b>\s*(\d+)</b>', text)

    # 构建结果字典
    result = {}

    if sign_count:
        result['sign_in_count'] = int(sign_count.group(1))
    if continuous:
        result['continuous_days'] = int(continuous.group(1))
    if magic_earned:
        result['magic_earned'] = int(magic_earned.group(1))
    if total_magic:
        # 移除逗号并转换
        magic_str = total_magic.group(1).replace(',', '')
        result['total_magic'] = "{:,.2f}".format(float(magic_str))
    if QD_card:
        result['QD_card'] = int(QD_card.group(1))
    if rank_match:
        result['my_rank'] = int(rank_match.group(1))
        result['total_rank'] = int(rank_match.group(2))

    return result

# 使用示例
def main():
    # 待输入字符串格式Cookies
    cookies_str = ""

    # 创建session
    session = create_session_with_retry(cookies_str)

    # 添加Referer和Origin（根据实际站点修改）
    session.headers.update({
        'Referer': 'https://t.myaltbox.com/index.php',
        'Origin': 'https://t.myaltbox.com'
    })

    # 尝试访问首页获取必要的token或验证信息
    try:
        # 先访问首页，让服务器建立连接
        print("访问首页...")
        home_response = safe_request(session, 'GET', 'https://t.myaltbox.com/index.php')

        if home_response.status_code == 200 and "Eulogy" in home_response.text:
            print("✅ 登录成功!")
        else:
            print(f"❌ 登录失败")


        # 然后执行签到
        print("执行签到...")
        sign_response = safe_request(session, 'GET', 'https://t.myaltbox.com/attendance.php')

        # 处理响应
        if sign_response.status_code == 200 and "签到成功" in sign_response.text:
            print("✅ 签到成功!")
            # print(sign_response.text[:500])  # 打印前500字符

            # --------------------------------获取奖励信息------------------------------------------------------------------------

            info = parse_sign_in_info(sign_response.text)

            # 输出结果
            print("签到信息:")
            print(f"  总计签到天数: {info.get('sign_in_count', '未找到')}")
            print(f"  连续签到天数: {info.get('continuous_days', '未找到')}")
            print(f"  本次获取魔力: {info.get('magic_earned', '未找到')}")
            print(f"  累计魔力总值: {info.get('total_magic', '未找到')}")
            print(f"  补签卡数量: {info.get('QD_card', '未找到')}")
            print(f"  今日签到排名: {info.get('my_rank', '未找到')}/{info.get('total_rank', '未找到')}")

            print("✅ 获取奖励信息成功！")


        else:
            print(f"❌ 签到失败，状态码: {sign_response.status_code}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")

    finally:
        session.close()


if __name__ == '__main__':
    main()
