"""
用于金鹰签到获取积分
需要 Cookie
"""



import requests
import json5

# 定义请求的 URL
url = "https://go.jinying.com/ajax_session/activity/check_in?do=check&share_user_id=0"


# 原始 cookie 字符串
cookie_str = ""

# 将 cookie 字符串转换为字典
cookies = {}
for cookie in cookie_str.split(';'):
    key, value = cookie.strip().split('=', 1)  # 分割键值对，去掉多余空格
    cookies[key] = value  # 将键值对添加到字典


# 发送 GET 请求
response = requests.get(url, cookies=cookies)

# 获取状态码和网页内容
status_code = response.status_code
content = response.text

# 输出状态码和内容
print(f"网页状态码: {status_code}")

# 解析 JSON 字符串
data = json5.loads(content)

# 输出结果
print(f"code: {data['code']}, desc: {data['desc']}")
