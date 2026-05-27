import re
from dataclasses import replace
import requests
import time
import urllib.parse
from http.cookies import SimpleCookie
import random
from bs4 import BeautifulSoup
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

"""
用于 PTtime 签到保号
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
    cookies_dict = cookie_str_to_dict(cookies_str)
    session.cookies.update(cookies_dict)

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
    time.sleep(random.uniform(1, 3))
    try:
        response = session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        if "Connection reset by peer" in str(e):
            print("检测到连接重置，增加延迟并重试...")
            time.sleep(5)
        raise
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        raise

# ==================== 记录页解析函数 ====================

def parse_check_info(soup):
    """
    解析签到后页面的基本签到信息
    """
    check_info={}
    td = soup.find_all('td', class_='embedded')[1]
    if not td:
        return check_info

    if '今日签到成功' in td.text:
        check_info['status']='今日签到成功'
        content = td.find('ul').find('li').find_all('b')
        check_info['sign_count']=content[0].text
        check_info['continuous_days']=content[1].text
        check_info['magic_value']=content[2].text

    elif '今天已签到' in td.text:
        check_info['status']='今天已签到'
        content = td.find('b')
        check_info['refresh_times'] = content.text

    # header = td.find('p', class_='mt10 fwb', string='总签到记录')

    return check_info

def parse_magic_value(soup):
    """
    从页面中提取魔力值信息
    输入HTML示例：
    <span class="mr5"><font>魔力值(74.99魔力/小时)</font>
    [<a href="mybonus.php" class="fcs">使用&说明</a>]: 38232.0[<a href="attendance.php?type=list" class="fcs">签到详情</a><font color="gray">(补签卡0枚)</font>]</span>
    """
    magic_info = {}
    # 查找包含“魔力值”的span
    magic_span = soup.find('span', class_='mr5', string=lambda t: t and '魔力值' in t)
    if not magic_span:
        # 尝试通过font标签定位
        font = soup.find('font', string=re.compile(r'魔力值'))
        if font:
            magic_span = font.find_parent('span', class_='mr5')
    if magic_span:
        full_text = magic_span.get_text(' ', strip=True)  # 用空格连接，便于正则
        # 提取每小时速率
        rate_match = re.search(r'魔力值\(([\d.]+)魔力/小时\)', full_text)
        if rate_match:
            magic_info['hourly_rate'] = "{:,.2f}".format(float(rate_match.group(1).replace(',', '')))
        # 提取当前魔力值（冒号后的数字，可能带逗号）
        value_match = re.search(r':\s*([\d,]+\.?\d*)', full_text)
        if value_match:
            magic_info['current_value'] = "{:,.2f}".format(float(value_match.group(1).replace(',', '')))
        # 提取补签卡数量
        card_match = re.search(r'补签卡(\d+)枚', full_text)
        if card_match:
            magic_info['repair_cards'] = int(card_match.group(1))
    return magic_info



def parse_total_attendance(soup):
    """
    提取总签到记录信息
    输入HTML示例：
    <td class="embedded"><p class="mt10 fwb">总签到记录</p><span>总签到：7天</span><span class="ml10">等级：<b title="签到等级：日级 OR 2/7级">🌙</b></span><span class="ml50">第一次签到：2026-02-08 23:00:26</span><span class="ml10">距今：3周前</span><span class="ml50">本次连续签到开始时间：20260225</span>...
    """
    total_info = {}
    # 定位包含总签到记录的td（或者直接找p标签）
    # 方法1：找到class为embedded的td，然后找内部p
    td = soup.find_all('td', class_='embedded')[1]
    if not td:
        return total_info
    header = td.find('p', class_='mt10 fwb', string='总签到记录')
    if not header:
        return total_info

    # 获取该p后面的所有文本（但需要精确提取各项）
    # 我们可以直接在td内搜索各个span
    total_span = td.find('span', string=re.compile(r'总签到：'))
    if total_span:
        match = re.search(r'总签到：(\d+)天', total_span.get_text())
        if match:
            total_info['total_days'] = int(match.group(1))

    # total_info['level_title'] = td.find('b', title='签到等级：日级 OR 2/7级').text
    total_info['level_title'] = f"""{td.select_one('b[title^="签到等级："]').text}|{td.select_one('b[title^="签到等级："]')['title'].replace('签到等级：','')}"""

    total_info['before_present'] = td.find_all('span', class_='ml10')[1].text.replace("距今：","")

    first_span = td.find('span', class_='ml50', string=re.compile(r'第一次签到：'))
    if first_span:
        match = re.search(r'第一次签到：([\d-]+ [\d:]+)', first_span.get_text())
        if match:
            total_info['first_sign'] = match.group(1)

    cont_start_span = td.find('span', class_='ml50', string=re.compile(r'本次连续签到开始时间：'))
    if cont_start_span:
        match = re.search(r'本次连续签到开始时间：(\d+)', cont_start_span.get_text())
        if match:
            total_info['continuous_start'] =  str(int(match.group(1)[:4]))+'-'+ str(format(match.group(1)[4:6],"00"))+'-'+ str(format(match.group(1)[6:],'00'))

    return total_info


def parse_7day_attendance(soup):
    """
    提取7天签到记录
    输入HTML片段中的一系列span条目
    """
    records = {}
    td = soup.find_all('td', class_='embedded')[1]
    if not td:
        return records

    # 获取签到时间
    t_tags = td.find_all('span', class_='dib w200 pr20')
    if not t_tags:
        return records
    # 获取魔力值
    m_tags = td.find_all('span', class_='dib w150')
    # 获取连续签到天数与连续等级
    l_tags = td.find_all('span', class_='ml20')
    lc=l_tags.__len__

    for i in range(0,7):
        if len(t_tags[i].text)>13:
            # .find('span', class_='ml20').find('b', title=True)

            records[i]=t_tags[i].text.ljust(25)+'获得魔力值：'+m_tags[i].find('b').text.ljust(6)+l_tags[2*i].text.ljust(8)+f"{l_tags[2*i+1].text+l_tags[2 * i + 1].find('b').find('b')['title']}".ljust(16)
        else:
            records[i]=t_tags[i].text.ljust(25)+'签到中止'
    return records

def parse_30day_attendance(soup):
    """
    提取前 30天签到记录
    输入HTML片段中的一系列span条目
    """
    records = []
    p = soup.find('p', string=lambda t: t and '前30天签到记录' in t)
    if not p:
        return records


    # 获取p之后的所有span
    spans = p.find_all_next('span')  # 这会在整个文档中寻找，可能包含后面的span，但后面已经没有span了？实际上在示例中，后面还有<br>和</td>，但没有span了。
    # 更好的方法是只取到下一个p之前的span。可以使用while循环遍历兄弟节点。
    # 使用find_next_siblings直到遇到p。
    spans_in_section = []
    for sib in p.next_siblings:
        if sib.name == 'p':
            break
        if sib.name == 'span':
            spans_in_section.append(sib)
    # 现在spans_in_section包含了所有的span，按顺序成对出现：连续天数span，签到日span
    for i in range(0, len(spans_in_section), 2):
        if i + 1 >= len(spans_in_section):
            break
        span1 = spans_in_section[i]
        span2 = spans_in_section[i + 1]
        if '连续天数：' in span1.get_text() and '签到日：' in span2.get_text():
            cont_days = re.search(r'连续天数：(\d+)', span1.get_text()).group(1)
            date = re.search(r'签到日：(\d+)', span2.get_text()).group(1)
            records.append({'continuous_days': int(cont_days), 'date': str(int(date[:4]))+'-'+ str(format(date[4:6],"00"))+'-'+ str(format(date[6:],'00'))})
    return records



def parse_attendance_list_page(html):
    """
    解析签到记录页面，返回包含魔力值、总签到、7天签到的字典
    """
    soup = BeautifulSoup(html, 'html.parser')
    return {
        'check_info': parse_check_info(soup),
        'magic': parse_magic_value(soup),
        'total_attendance': parse_total_attendance(soup),
        '7day_attendance': parse_7day_attendance(soup),
        '30day_attendance': parse_30day_attendance(soup)
    }





# ==================== 主函数 ====================

def main():
    cookies_str = ""

    session = create_session_with_retry(cookies_str)
    session.headers.update({
        'Referer': 'https://www.pttime.org/index.php',
        'Origin': 'https://www.pttime.org/'
    })

    try:
        # 1. 访问首页检查登录
        print("访问首页...")
        home_response = safe_request(session, 'GET', 'https://www.pttime.org/index.php')
        if home_response.status_code == 200 and "Eulogy" in home_response.text:
            print("✅ 登录成功!")
        else:
            print("❌ 登录失败，可能 cookies 过期")
            return

        # 2. 签到；获取并解析签到记录页面

        record_url = f"https://www.pttime.org/attendance.php?type=sign&userid=114621"
        print(f"\n 请求签到记录页面: {record_url}")
        record_response = safe_request(session, 'GET', record_url)

        if record_response.status_code == 200:
            print("\n ✅ 今日签到成功")

            record_data = parse_attendance_list_page(record_response.text)

            print("\n【今日签到情况】")
            check_info=record_data.get('check_info', {})
            if check_info!={} and check_info['status'] == '今日签到成功':
                print('  ✅ 今日签到成功')
                print(f"  这是你的第 {check_info['sign_count']} 次签到，已连续签到 {check_info['continuous_days']} 天，本次签到获得 {check_info['magic_value']} 个魔力值。")
            elif check_info!={} and check_info['status'] == '今天已签到':
                print('  ✅ 今天已签到!')
                print(f"  请勿重复刷新(高频高量刷新可能导致封号)。")
                print(f"  已刷次数：{check_info['refresh_times']}次。")
            elif check_info == {}:
                print('  无法获取当日签到情况！\n  一般是因为当日签到刷新次数过多！')
                # 重新获取签到统计数据
                record_url = f"https://www.pttime.org/attendance.php?type=list"
                print(f"  请求重新获取签到统计数据: {record_url}")
                record_response = safe_request(session, 'GET', record_url)
                record_data = parse_attendance_list_page(record_response.text)

            print('\n  首次签到获得 10 个魔力值。每次签到可额外获得 5 个魔力值，直到 100 封顶。\n  连续签到 10 天后，每次签到额外获得 100 魔力值（不累计）。\n  连续签到 20 天后，每次签到额外获得 300 魔力值（不累计）。\n  连续签到 30 天后，每次签到额外获得 500 魔力值（不累计）。')

            print("\n【魔力值详情】")
            magic = record_data.get('magic', {})
            print(f"  当前魔力值: {magic.get('current_value', 'N/A')}")
            print(f"  每小时生成: {magic.get('hourly_rate', 'N/A')}")

            print("\n【总签到记录】")
            total = record_data.get('total_attendance', {})
            print(f"  总 签 到 天 数: {total.get('total_days', 'N/A')}")
            print(f"  签  到  等  级: {total.get('level_title', 'N/A')}")
            print(f"  距         今: {total.get('before_present', 'N/A')}")
            print(f"  第 一 次 签 到: {total.get('first_sign', 'N/A')}")
            print(f"  本次连续签到开始: {total.get('continuous_start', 'N/A')}")

            print("\n【7天签到记录】")
            sevenday = record_data.get('7day_attendance', [])
            if sevenday:
                for i in range(0,7):
                    print(f"  {sevenday[i]}")
            else:
                print("  未找到7天签到记录")

            print("\n【前30天签到记录】")
            sevenday = record_data.get('30day_attendance', [])
            if sevenday:
                for i in sevenday:
                    print(f"  连续天数：{str(i['continuous_days']).ljust(10)}签到日：{i['date'].ljust(16)}")
            else:
                print("  未找到30天签到记录")
        else:
            print(f"❌ 无法获取签到记录页，状态码: {record_response.status_code}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")
    finally:
        session.close()


if __name__ == '__main__':
    main()
