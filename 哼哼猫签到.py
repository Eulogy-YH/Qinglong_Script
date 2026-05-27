
"""
用于 哼哼猫签到获取免费次数
用法：在第一步输入账号密码
"""

import requests

# ---------- 第一步：登录获取 sessionID ----------
login_url = "https://api.feeprint.com/auth/login"
login_payload = {
    "account": "账号",
    "password": "密码"
}
login_headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh",
    "dnt": "1",
    "g-timezone": "Asia/Shanghai",
    "origin": "https://www.henghengmao.com",
    "referer": "https://www.henghengmao.com/",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
}

print("正在登录...")
login_resp = requests.post(login_url, json=login_payload, headers=login_headers)
if login_resp.status_code != 200:
    print("❌ 登录失败，状态码：", login_resp.status_code)
    print("   响应内容：", login_resp.text)
    exit()
login_data = login_resp.json()
session_id = login_data.get("sessionID")
print("✅ 登录成功，sessionID:", session_id)

# ---------- 第二步：每日签到 ----------
checkin_url = "https://api.feeprint.com/user/check-in"

# 构建签到请求头，包含从登录获得的 sessionID
checkin_headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh",
    "content-type": "application/json",      # 即使请求体为空，也要声明类型
    "dnt": "1",
    "g-session-id": session_id,              # 关键：将 sessionID 放在此头部
    "g-timezone": "Asia/Shanghai",
    "origin": "https://www.henghengmao.com",
    "referer": "https://www.henghengmao.com/",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
}

# 签到请求体为空（POST 请求但无数据）
# 注意：如果服务器要求 JSON 格式的空对象，可以传 {}，但这里 content-length 为 0，说明不传任何数据。
# 使用 json={} 会发送 b'{}'，content-length 为 2，可能导致错误。所以应该传 None 或空字符串。
# 在 requests 中，如果不传 data 或 json，默认就是空 body。我们显式不传即可。
print(r'https://www.henghengmao.com')
print("\n正在签到...")
checkin_resp = requests.post(checkin_url, headers=checkin_headers)  # 不传 data/json，body 为空

print("   签到状态码：", checkin_resp.status_code)
print("   签到响应：", checkin_resp.text)

print("\n签到结果...")
if checkin_resp.status_code == 200:
    result = checkin_resp.json()
    print("✅ 签到成功！\n   剩余可用次数：", result.get("availableTimes"))
    print("   连续签到天数：", result.get("checkInDays"))
elif checkin_resp.status_code == 400 and checkin_resp.text==r'{"message":"您已签到，请明天再来"}':
    print("✅ 今日已签到成功！")
else:
    print("❌ 签到失败，请检查头部或 sessionID 是否有效。")
