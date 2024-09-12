import os
import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

import poplib
import hashlib
import json
import random
import re
import time
import requests
import uuid
import email

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from pywebio.input import input_group, input, TEXT
from pywebio.output import put_text, put_markdown, clear, put_html
from pywebio import start_server
# from datetime import datetime
from pywebio.platform.flask import webio_view

app = Flask(__name__)

# -------------改这里-------------
# r'替换为自己txt文件所在地址'
file_path = r'./email.txt'

# 卡密文件路径
card_keys_file = r'./card_keys.json'

# 公告内容文件
JSON_FILE_PATH = r'./announcement.json'

# 读取公告内容
def read_announcement():
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

# 保存公告内容
def save_announcement(data):
    with open(JSON_FILE_PATH, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 提供公告内容的API，返回JSON格式公告
@app.route('/api/announcement', methods=['GET'])
def api_announcement():
    announcement_data = read_announcement()
    return jsonify(announcement_data)

# 从文件加载卡密信息
def load_card_keys():
    try:
        with open(card_keys_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # 如果文件不存在，返回一个空字典
        return {}

# 保存卡密信息到文件
def save_card_keys(card_keys):
    with open(card_keys_file, 'w') as f:
        json.dump(card_keys, f)

# 初始化卡密信息
card_keys = load_card_keys()

# 使用卡密时，减少次数并保存
def use_card_key(key):
    if key in card_keys and card_keys[key] > 0:
        card_keys[key] -= 1
        save_card_keys(card_keys)  # 保存使用后的状态
        return True
    return False

# --------------------------------


app.secret_key = 'key-huwe8sakeh82sad'  # 用于加密 session


# 读取 email.txt 文件内容
def read_emails():
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    return [line.strip() for line in lines]

# 写入 email.txt 文件内容
def write_emails(emails):
    with open(file_path, 'w', encoding='utf-8') as file:
        for email in emails:
            file.write(f"{email}\n")

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 简单验证，用户名和密码硬编码为 'admin' 和 'password'
        # 请自行更改账号密码
        if username == 'admin' and password == 'password':
            session['logged_in'] = True
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误，请重试。', 'danger')
    
    return render_template('login.html')

# 退出登录
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('您已成功退出登录。', 'success')
    return redirect(url_for('login'))

# 首页路径 email 
@app.route('/email')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    emails = read_emails()
    return render_template('index.html', emails=emails)

# 公告编辑页面
@app.route('/edit_announcement', methods=['GET', 'POST'])
def edit_announcement():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        # 获取表单数据
        enable = request.form.get('enable') == 'on'
        title = request.form.get('title')
        message = request.form.get('message')  # HTML富文本公告内容

        # 更新JSON文件内容
        announcement_data = {
            "enable": enable,
            "title": title,
            "message": message
        }
        save_announcement(announcement_data)
        flash('保存成功', 'success')
        # 重定向到编辑页面
        return redirect(url_for('edit_announcement'))

    # 如果是GET请求，读取公告并显示
    announcement_data = read_announcement()
    return render_template('edit_announcement.html', announcement=announcement_data)

# 显示并修改、添加卡密的页面
@app.route('/card', methods=['GET', 'POST'])
def card_info():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        # 更新已有卡密的次数
        for key in card_keys.keys():
            new_count = request.form.get(key)
            if new_count:
                card_keys[key] = int(new_count)
        
        # 处理可选的新增卡密部分
        new_key = request.form.get('new_key')
        new_key_count = request.form.get('new_key_count')
        if new_key and new_key_count:
            card_keys[new_key] = int(new_key_count)
        
        save_card_keys(card_keys)  # 保存更新后的卡密信息
        return redirect(url_for('card_info'))  # 刷新页面
    
    return render_template('card_edit.html', card_keys=card_keys)

# 删除卡密的路由
@app.route('/delete/<key>')
def delete_key(key):
    if key in card_keys:
        del card_keys[key]  # 从字典中删除卡密
        save_card_keys(card_keys)  # 保存删除后的卡密信息
    return redirect(url_for('card_info'))  # 返回卡密页面并刷新


# 批量添加页面
@app.route('/bulk_add', methods=['GET', 'POST'])
def bulk_add():
    # 去掉下面两行，关闭登陆验证
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    emails = read_emails()
    non_logged_in_emails = [email for email in emails if '登录成功' not in email and '失败' not in email]
    non_logged_in_count = len(non_logged_in_emails)
    
    # 获取最新的邮箱数量信息
    email_counts = get_email_counts()
    # 检查是否提供 key 值
    card_key = session.get('card', 'JH5V5BDWBGF9WDU4J9F8DOQCLHIHZ7Z3W7UFM94VV0V8A3117')  # 默认值
    
    # 获取最新的余额信息
    balance_info = get_balance(card_key)
    
    bulk_input = ""  # 初始化为空字符串

    if request.method == 'POST':
        # 更新 key 值
        if 'set_card' in request.form:
            session['card'] = request.form['card']
            flash('Key值已更新！', 'success')
            return redirect(url_for('bulk_add'))
        
        elif 'fetch_emails' in request.form:
            email_type = request.form['email_type']
            email_quantity = int(request.form['email_quantity'])

            # 调用API获取邮箱账号
            response = requests.get('https://zizhu.shanyouxiang.com/huoqu', params={
                'card': card_key,
                'shuliang': email_quantity,
                'leixing': email_type
            })

            if response.status_code == 200:
                bulk_input = response.text.strip()  # 获取的账号数据

                # 获取最新的邮箱数量信息
            email_counts = get_email_counts()

            # 获取最新的余额信息
            balance_info = get_balance(card_key)

            emails = read_emails()
            non_logged_in_emails = [email for email in emails if '登录成功' not in email and '失败' not in email]
            non_logged_in_count = len(non_logged_in_emails)

        elif 'manual_input' in request.form:
            bulk_input = request.form['bulk_input']
            new_emails = bulk_input.splitlines()
            emails = read_emails()
            for entry in new_emails:
                if '----' in entry:
                    emails.append(entry.strip())
            write_emails(emails)
            emails = read_emails()
            non_logged_in_emails = [email for email in emails if '登录成功' not in email and '失败' not in email]
            non_logged_in_count = len(non_logged_in_emails)
            flash('账号添加成功！', 'success')

        elif 'file_upload' in request.files:
            file = request.files['file_upload']
            if file and file.filename.endswith('.txt'):
                emails = read_emails()
                for line in file:
                    line = line.decode('utf-8').strip()
                    if '----' in line:
                        emails.append(line)
                write_emails(emails)
                emails = read_emails()
                non_logged_in_emails = [email for email in emails if '登录成功' not in email and '失败' not in email]
                non_logged_in_count = len(non_logged_in_emails)
                flash('文件上传账号添加成功！', 'success')
            else:
                flash('请上传有效的文本文件。', 'danger')

        # 再次渲染页面时传递 bulk_input 变量
        return render_template('bulk_add.html', non_logged_in_count=non_logged_in_count, email_counts=email_counts, balance_info=balance_info, bulk_input=bulk_input)

    return render_template('bulk_add.html', non_logged_in_count=non_logged_in_count, email_counts=email_counts, balance_info=balance_info, bulk_input=bulk_input)

# 获取 email 数量数据
def get_email_counts():
    url = 'https://zizhu.shanyouxiang.com/kucun'
    try:
        response = requests.get(url)
        response.raise_for_status()  # 如果状态码不是200，抛出HTTPError异常
        data = response.json()
        return data
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return {"hotmail": 0, "outlook": 0}  # 如果请求失败，返回默认数据


# 获取余额信息
def get_balance(card):
    url = 'https://zizhu.shanyouxiang.com/yue'
    params = {'card': card}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # 如果状态码不是200，抛出HTTPError异常
        data = response.json()
        return data
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return {"num": 0}  # 如果请求失败，返回默认数据


# 会员账号页面
@app.route('/public_emails')
def recent_emails():
    # 去掉下面两行，关闭登陆验证
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    emails = read_emails() 
    now = datetime.datetime.now()
    three_days_ago = now - datetime.timedelta(days=3)
    
    recent_emails = []

    for email in emails:
        # 检查是否包含"登录成功"
        if '登录成功' in email:
            parts = email.split(' ')  # 使用空格分隔
            try:
                # 获取时间戳部分并转换为 datetime 对象
                timestamp = datetime.datetime.fromtimestamp(float(parts[-1]))

                # 检查时间戳是否在最近三天内
                if timestamp >= three_days_ago:
                    account_info = email.split('----')  # 使用 '----' 分隔账号信息
                    account = account_info[0]  # 获取邮箱部分
                    fixed_password = "pik123"  # 固定密码 需要和下面邀请部分的密码一致
                    formatted_email = f"{account}----{fixed_password}"
                    recent_emails.append(formatted_email)
            except (ValueError, IndexError):
                continue

    return render_template('public_emails.html', recent_emails=recent_emails)


# 删除 email
@app.route('/delete/<int:index>')
def delete_email(index):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    emails = read_emails()
    if 0 <= index < len(emails):
        emails.pop(index)
        write_emails(emails)
    return redirect(url_for('index'))

# 更新 email
@app.route('/update/<int:index>', methods=['POST'])
def update_email(index):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    new_email = request.form['new_email']
    new_password = request.form['new_password']
    emails = read_emails()
    if 0 <= index < len(emails):
        emails[index] = f"{new_email}----{new_password}"
        write_emails(emails)
    return redirect(url_for('index'))
# 以下为会员邀请部分
# 读取文件内容提取邮箱和密码，跳过包含登录成功或登录成功(待定)的行
def read_and_process_file(file_path):
    try:
        email_user_list = []
        email_pass_list = []
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        updated_lines = []
        for line in lines:
            line = line.strip()
            if "登录成功" in line or "登录成功(待定)" in line or "失败" in line:
                continue
            match = re.match(r'^(.+?)----([^\s@]+)$', line)
            if match:
                email, password = match.groups()
                email_user_list.append(email)
                email_pass_list.append(password)
            else:
                print(f"无法匹配行: {line}")
                updated_lines.append(line)

        return email_user_list, email_pass_list
    except Exception as e:
        print("读取文件失败:", e)
        return None, None

# 更新文件
def update_file_status(file_path, email, password, status, time):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        with open(file_path, 'w', encoding='utf-8') as file:
            for line in lines:
                if line.strip().startswith(email) and "----" in line:
                    file.write(f"{line.strip()} {status} {time}\n")
                else:
                    file.write(line)
    except Exception as e:
        print("更新文件状态失败:", e)

# POP微软邮箱登录
def get_email_with_third_party(recipient_email, email_user, email_pass, delay=2, max_retries=10):
    pop3_server = "pop-mail.outlook.com"
    retries = 0
    while retries < max_retries:
        try:
            mail = poplib.POP3_SSL(pop3_server)
            mail.user(email_user)
            mail.pass_(email_pass)
            num_messages = len(mail.list()[1])
            for i in range(num_messages):
                response, lines, octets = mail.retr(i + 1)
                raw_email = b'\n'.join(lines)
                code = process_email(raw_email, i + 1, mail)
                if code:
                    return code
            mail.quit()
        except Exception as e:
            print(f"发生错误: {e}")
        retries += 1
        time.sleep(delay)
    return None


# 读取邮箱中验证码
def process_email(raw_email, email_id, mail):
    email_message = email.message_from_bytes(raw_email)
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == 'text/plain' and not part.get('Content-Disposition'):
                body = part.get_payload(decode=True)
                body_text = body.decode('utf-8')
                match = re.search(r'\d{6}', body_text)
                if match:
                    code = match.group()
                    print(f'获取到验证码: {code}')
                    return code
    else:
        body = email_message.get_payload(decode=True)
        body_text = body.decode('utf-8')
        match = re.search(r'\d{6}', body_text)
        if match:
            code = match.group()
            print(f'获取到验证码: {code}')
            return code
    print("邮件正文为空或无法解码")
    return None


# 邀请成功结果推送到微信
def wxpusher(new_email, password, invitation_code):
    global randint_ip
    app_token = ""
    if app_token:
        api_url = "https://wxpusher.zjiecode.com/api/send/message"
        data = {
            "appToken": app_token,
            "summary": "邀请成功: " + invitation_code,
            "content": "<h1>PikPak运行结果通知🔔</h1><br/><h3>邀请码：" + invitation_code + "</h3><h4>账户：" + new_email + "</h4><h4>密码：" + password + "</h4>",
            "contentType": 2,
            "topicIds": [30126],
            "uids": [],
            "verifyPayType": 0
        }
        headers = {
            # X-Forwarded-For': str(randint_ip)
        }
        json_data = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(api_url, headers=headers, data=json_data)
        data = response.json()
    # print(f'wxpusher推送结果：{data["msg"]}')


# 动态代理
def get_proxy():
    # 请更改为你自己的代理池地址
    proxy_uri = requests.get('https://example.com/fetch_random').text
    
    if len(proxy_uri) == 0:
        proxies = {}
        # print('获取代理失败')
    else:
        proxies = {
            # 如果你不想使用代理池，请把下面两条语句删掉
            # 不使用极大概率奖励不生效
            'http': proxy_uri,
            'https': proxy_uri
        }
        # print('获取代理成功')
    return proxies


def get_randint_ip():
    m = random.randint(0, 255)
    n = random.randint(0, 255)
    x = random.randint(0, 255)
    y = random.randint(0, 255)
    randomIP = str(m) + '.' + str(n) + '.' + str(x) + '.' + str(y)
    return randomIP


randint_ip = get_randint_ip()


# 加密算法
def r(e, t):
    n = t - 1
    if n < 0:
        n = 0
    r = e[n]
    u = r["row"] // 2 + 1
    c = r["column"] // 2 + 1
    f = r["matrix"][u][c]
    l = t + 1
    if l >= len(e):
        l = t
    d = e[l]
    p = l % d["row"]
    h = l % d["column"]
    g = d["matrix"][p][h]
    y = e[t]
    m = 3 % y["row"]
    v = 7 % y["column"]
    w = y["matrix"][m][v]
    b = i(f) + o(w)
    x = i(w) - o(f)
    return [s(a(i(f), o(f))), s(a(i(g), o(g))), s(a(i(w), o(w))), s(a(b, x))]


def i(e):
    return int(e.split(",")[0])


def o(e):
    return int(e.split(",")[1])


def a(e, t):
    return str(e) + "^⁣^" + str(t)


def s(e):
    t = 0
    n = len(e)
    for r in range(n):
        t = u(31 * t + ord(e[r]))
    return t


def u(e):
    t = -2147483648
    n = 2147483647
    if e > n:
        return t + (e - n) % (n - t + 1) - 1
    if e < t:
        return n - (t - e) % (n - t + 1) + 1
    return e


def c(e, t):
    return s(e + "⁣" + str(t))


def img_jj(e, t, n):
    return {"ca": r(e, t), "f": c(n, t)}


def uuid():
    return ''.join([random.choice('0123456789abcdef') for _ in range(32)])


def md5(input_string):
    return hashlib.md5(input_string.encode()).hexdigest()


def get_sign(xid, t):
    e = [
        {"alg": "md5", "salt": "KHBJ07an7ROXDoK7Db"},
        {"alg": "md5", "salt": "G6n399rSWkl7WcQmw5rpQInurc1DkLmLJqE"},
        {"alg": "md5", "salt": "JZD1A3M4x+jBFN62hkr7VDhkkZxb9g3rWqRZqFAAb"},
        {"alg": "md5", "salt": "fQnw/AmSlbbI91Ik15gpddGgyU7U"},
        {"alg": "md5", "salt": "/Dv9JdPYSj3sHiWjouR95NTQff"},
        {"alg": "md5", "salt": "yGx2zuTjbWENZqecNI+edrQgqmZKP"},
        {"alg": "md5", "salt": "ljrbSzdHLwbqcRn"},
        {"alg": "md5", "salt": "lSHAsqCkGDGxQqqwrVu"},
        {"alg": "md5", "salt": "TsWXI81fD1"},
        {"alg": "md5", "salt": "vk7hBjawK/rOSrSWajtbMk95nfgf3"}
    ]
    md5_hash = f"YvtoWO6GNHiuCl7xundefinedmypikpak.com{xid}{t}"
    for item in e:
        md5_hash += item["salt"]
        md5_hash = md5(md5_hash)
    return md5_hash

# 初始安全验证
def init(xid, mail):
    global randint_ip
    url = 'https://user.mypikpak.com/v1/shield/captcha/init'
    body = {
        "client_id": "YvtoWO6GNHiuCl7x",
        "action": "POST:/v1/auth/verification",
        "device_id": xid,
        "captcha_token": "",
        "meta": {
            "email": mail
        }
    }
    headers = {
        'host': 'user.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'MainWindow Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'PikPak/2.3.2.4101 Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'accept-language': 'zh-CN',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-device-model': 'electron%2F18.3.15',
        'x-device-name': 'PC-Electron',
        'x-device-sign': 'wdi10.ce6450a2dc704cd49f0be1c4eca40053xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'x-net-work-type': 'NONE',
        'x-os-version': 'Win32',
        'x-platform-version': '1',
        'x-protocol-version': '301',
        'x-provider-name': 'NONE',
        'x-sdk-version': '6.0.0',
        'X-Forwarded-For': str(randint_ip)
    }
    retries = 0
    max_retries = 3
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('初始安全验证')
            return response_data
        except:
            retries += 1

# 获取token
def get_new_token(xid, captcha):
    retries = 0
    max_retries = 3
    while retries < max_retries:
        try:
            response2 = requests.get(
                f"https://user.mypikpak.com/credit/v1/report?deviceid={xid}&captcha_token={captcha}&type"
                f"=pzzlSlider&result=0", proxies=get_proxy(), timeout=5)

            response_data = response2.json()
            # print('获取验证TOKEN中......')
            return response_data
        except:
            retries += 1
    return '连接超时'
# 发送验证码
def verification(captcha_token, xid, mail):
    global randint_ip
    url = 'https://user.mypikpak.com/v1/auth/verification'
    body = {
        "email": mail,
        "target": "ANY",
        "usage": "REGISTER",
        "locale": "zh-CN",
        "client_id": "YvtoWO6GNHiuCl7x"
    }
    headers = {
        'host': 'user.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'MainWindow Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'PikPak/2.3.2.4101 Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'accept-language': 'zh-CN',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-captcha-token': captcha_token,
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-device-model': 'electron%2F18.3.15',
        'x-device-name': 'PC-Electron',
        'x-device-sign': 'wdi10.ce6450a2dc704cd49f0be1c4eca40053xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'x-net-work-type': 'NONE',
        'x-os-version': 'Win32',
        'x-platform-version': '1',
        'x-protocol-version': '301',
        'x-provider-name': 'NONE',
        'x-sdk-version': '6.0.0'
        # 'X-Forwarded-For': str(randint_ip)
    }

    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('发送验证码')
            return response_data
        except:
            retries += 1


# 验证码结果
def verify(xid, verification_id, code):
    global randint_ip
    url = 'https://user.mypikpak.com/v1/auth/verification/verify'
    body = {
        "verification_id": verification_id,
        "verification_code": code,
        "client_id": "YvtoWO6GNHiuCl7x"
    }
    headers = {
        'host': 'user.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'MainWindow Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'PikPak/2.3.2.4101 Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'accept-language': 'zh-CN',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-device-model': 'electron%2F18.3.15',
        'x-device-name': 'PC-Electron',
        'x-device-sign': 'wdi10.ce6450a2dc704cd49f0be1c4eca40053xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'x-net-work-type': 'NONE',
        'x-os-version': 'Win32',
        'x-platform-version': '1',
        'x-protocol-version': '301',
        'x-provider-name': 'NONE',
        'x-sdk-version': '6.0.0'
        # 'X-Forwarded-For': str(randint_ip)
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('验证码验证结果')
            # 遍历 details 列表，检查是否有包含 '验证码不正确' 的 message
            for detail in response_data.get('details', []):
                if 'message' in detail and '验证码不正确' in detail['message']:
                    return '验证码不正确'
            return response_data
        except:
            retries += 1


# 验证注册结果
def signup(xid, mail, code, verification_token):
    global randint_ip
    url = 'https://user.mypikpak.com/v1/auth/signup'
    body = {
        "email": mail,
        "verification_code": code,
        "verification_token": verification_token,
        'name': f'qihang{random.randint(1, 1000000000)}vip',
        "password": "pik123",
        "client_id": "YvtoWO6GNHiuCl7x"
    }
    headers = {
        'host': 'user.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'MainWindow Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'PikPak/2.3.2.4101 Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'accept-language': 'zh-CN',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-device-model': 'electron%2F18.3.15',
        'x-device-name': 'PC-Electron',
        'x-device-sign': 'wdi10.ce6450a2dc704cd49f0be1c4eca40053xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'x-net-work-type': 'NONE',
        'x-os-version': 'Win32',
        'x-platform-version': '1',
        'x-protocol-version': '301',
        'x-provider-name': 'NONE',
        'x-sdk-version': '6.0.0'
        # 'X-Forwarded-For': str(randint_ip)
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('验证注册结果')
            return response_data
        except:
            retries += 1


# 二次安全验证
def init1(xid, access_token, sub, sign, t):
    global randint_ip
    url = 'https://user.mypikpak.com/v1/shield/captcha/init'
    body = {
        "client_id": "YvtoWO6GNHiuCl7x",
        "action": "POST:/vip/v1/activity/invite",
        "device_id": xid,
        "captcha_token": access_token,
        "meta": {
            "captcha_sign": "1." + sign,
            "client_version": "undefined",
            "package_name": "mypikpak.com",
            "user_id": sub,
            "timestamp": t
        },
    }
    headers = {
        'host': 'user.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN',
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'MainWindow Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'PikPak/2.3.2.4101 Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-device-model': 'electron%2F18.3.15',
        'x-device-name': 'PC-Electron',
        'x-device-sign': 'wdi10.ce6450a2dc704cd49f0be1c4eca40053xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'x-net-work-type': 'NONE',
        'x-os-version': 'Win32',
        'x-platform-version': '1',
        'x-protocol-version': '301',
        'x-provider-name': 'NONE',
        'x-sdk-version': '6.0.0'
        # 'X-Forwarded-For': str(randint_ip)
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('通过二次安全验证')
            return response_data
        except:
            retries += 1


# 确认邀请
def invite(access_token, captcha_token, xid):
    global randint_ip
    url = 'https://api-drive.mypikpak.com/vip/v1/activity/invite'
    body = {
        "apk_extra": {
            "invite_code": ""
        }
    }
    headers = {
        'host': 'api-drive.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN',
        'authorization': 'Bearer ' + access_token,
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) PikPak/2.3.2.4101 '
                      'Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-captcha-token': captcha_token,
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-system-language': 'zh-CN'
        # 'X-Forwarded-For': str(randint_ip)
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('确认邀请')
            return response_data
        except:
            retries += 1


# 三次安全验证
def init2(xid, access_token, sub, sign, t):
    global randint_ip
    url = 'https://user.mypikpak.com/v1/shield/captcha/init'
    body = {
        "client_id": "YvtoWO6GNHiuCl7x",
        "action": "post:/vip/v1/order/activation-code",
        "device_id": xid,
        "captcha_token": access_token,
        "meta": {
            "captcha_sign": "1." + sign,
            "client_version": "undefined",
            "package_name": "mypikpak.com",
            "user_id": sub,
            "timestamp": t
        },
    }
    headers = {
        'host': 'user.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN',
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'MainWindow Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'PikPak/2.3.2.4101 Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-device-model': 'electron%2F18.3.15',
        'x-device-name': 'PC-Electron',
        'x-device-sign': 'wdi10.ce6450a2dc704cd49f0be1c4eca40053xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'x-net-work-type': 'NONE',
        'x-os-version': 'Win32',
        'x-platform-version': '1',
        'x-protocol-version': '301',
        'x-provider-name': 'NONE',
        'x-sdk-version': '6.0.0'
        # 'X-Forwarded-For': str(randint_ip)
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('通过三次安全验证')
            return response_data
        except:
            retries += 1


# 验证邀请码
def activation_code(access_token, captcha, xid, in_code):
    global randint_ip
    url = 'https://api-drive.mypikpak.com/vip/v1/order/activation-code'
    body = {
        "activation_code": in_code,
        "page": "invite"
    }
    headers = {
        'host': 'api-drive.mypikpak.com',
        'content-length': str(len(json.dumps(body))),
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN',
        'authorization': 'Bearer ' + access_token,
        'referer': 'https://pc.mypikpak.com',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) PikPak/2.3.2.4101 '
                      'Chrome/100.0.4896.160 Electron/18.3.15 Safari/537.36',
        'content-type': 'application/json',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-captcha-token': captcha,
        'x-client-id': 'YvtoWO6GNHiuCl7x',
        'x-client-version': '2.3.2.4101',
        'x-device-id': xid,
        'x-system-language': 'zh-CN',
        'X-Forwarded-For': str(randint_ip)
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('开始填写邀请码')
            # print(f'邀请结果:  {json.dumps(response_data, indent=4)}')
            return response_data
        except:
            retries += 1

# -------------------------- 主函数一系列网络请求--------------------------
invite_success_limit = 1
invitation_records = {}

def main(incode, card_key, num_invitations=5):
    now = datetime.datetime.now()
    print("当前日期: ", now)
    start_time = time.time()
    success_count = 0

    global invitation_records
    current_time = time.time()

    if incode in invitation_records:
        last_submissions = invitation_records[incode]
        last_submissions = [
            t for t in last_submissions if current_time - t < 36000] # 10小时
        if len(last_submissions) >= 1:
            return "24小时内已提交1次，请明日再试。"
        invitation_records[incode] = last_submissions
    else:
        invitation_records[incode] = []

    while success_count < num_invitations:
        try:
            xid = uuid()
            email_users, email_passes = read_and_process_file(file_path)

            if not email_users or not email_passes:
                return "暂无可用邮箱"

            for email_user, email_pass in zip(email_users, email_passes):
                mail = email_user

                # 执行初始化安全验证
                Init = init(xid, mail)
                captcha_token_info = get_new_token(xid, Init['captcha_token'])
                if (captcha_token_info == '连接超时'):
                     return "连接超时,请刷新重试，多次失败请联系管理员查看代理池"
                Verification = verification(
                    captcha_token_info['captcha_token'], xid, mail)

                # 获取验证码
                code = get_email_with_third_party(mail, email_user, email_pass)

                if not code:
                    print(f"无法从邮箱获取验证码: {mail}")
                    # 获取当前时间
                    current_timestamp = time.time()
                    update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
                    return "邮箱登录/验证失败，请刷新重试"

                # 使用验证码完成其他操作
                verification_response = verify(xid, Verification['verification_id'], code)
                if(verification_response == '验证码不正确'):
                    # 获取当前时间
                    current_timestamp = time.time()
                    update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
                    return '验证码不正确'
                signup_response = signup(xid, mail, code, verification_response['verification_token'])
                current_time = str(int(time.time()))
                sign = get_sign(xid, current_time)
                init1_response = init1(xid, signup_response['access_token'], signup_response['sub'], sign, current_time)
                invite(signup_response['access_token'],init1_response['captcha_token'], xid)
                init2_response = init2(xid, signup_response['access_token'], signup_response['sub'], sign, current_time)
                activation = activation_code(signup_response['access_token'], init2_response['captcha_token'], xid, incode)
                end_time = time.time()
                run_time = f'{(end_time - start_time):.2f}'

                # 检查邀请是否成功
                # 目前会员邀请之后会有最高24小时的审核，所以会一直显示失败
                # 如果会员天数等于5 邀请成功
                if activation.get('add_days') == 5:
                    result = f"邀请成功 邀请码: {incode} email: {mail} 密码：pik123"
                    print(result)
                    success_count += 1
                    # 邀请时间限制
                    invitation_records[incode].append(time.time())
                    # 获取当前时间
                    current_timestamp = time.time()
                    # 更新文件中的邮箱和密码状态 添加时间
                    update_file_status(file_path , email_user, email_pass, "登录成功", current_timestamp)
                    # 更新卡密使用次数
                    card_keys[card_key] -= 1
                    save_card_keys(card_keys)  # 保存更新后的卡密信息
                    return f"邀请成功: {incode} 运行时间: {run_time}秒<br> 邮箱: {mail} <br> 密码: pik123"
                # 如果会员天数等于0 邀请成功(待定)
                elif activation.get('add_days') == 0:
                    result = f'邀请成功(待定): {incode} 请重新打开邀请页面，查看邀请记录是否显示‘待定’'
                    print(result)
                    success_count += 1
                    # 邀请时间限制
                    invitation_records[incode].append(time.time())
                    # 获取当前时间
                    current_timestamp = time.time()
                    # 更新文件中的邮箱和密码状态 添加时间
                    update_file_status(r'./email.txt', email_user, email_pass, "登录成功(待定)", current_timestamp)
                    # 更新卡密使用次数
                    card_keys[card_key] -= 1
                    save_card_keys(card_keys)  # 保存更新后的卡密信息
                    return f"邀请成功(待定): {incode} 运行时间: {run_time}秒<br> 邮箱: {mail} <br> 密码: pik123 <br>请重新打开邀请页面，查看邀请记录是否显示‘待定’"
                else:
                    result = f"未知情况: {activation}"
                    print(result)
                    # 获取当前时间
                    current_timestamp = time.time()
                    update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
                    return result

        except Exception as e:
            # 检查异常信息并设置结果
            if "cannot unpack non-iterable NoneType object" in str(e):
                result = "异常: 临时邮箱暂没货，等待补货 预计1小时恢复"
            elif "add_days" in str(e):
                result = f"异常: {e} 检查邀请码是否有效 程序出错"
            elif 'captcha_token' in str(e):
                result = f"异常: {e} 临时邮箱暂没货，等待补货 预计1小时恢复"
            else:
                result = f'异常重试... {e}'
            print(result)
            return result

# html页面
from pywebio.output import put_html, clear, put_markdown
from pywebio.session import run_js
from concurrent.futures import ThreadPoolExecutor

from pywebio.output import put_html, clear, put_markdown, toast
from pywebio.session import eval_js
from concurrent.futures import ThreadPoolExecutor

# html页面
def web_app():
    put_html('''
            <style>
            /* 移除页面底部 */
            .footer {
                display: none !important;
            }

            /* 页头样式 */
            .pywebio_header {
                text-align: center;
                font-size: 26px;
                font-weight: bold;
                margin-bottom: 30px;
                color: #333;
                font-family: 'Arial', sans-serif;
                letter-spacing: 2px;
            }

            /* 说明文字样式 */
            .km_title {
                text-align: center;
                color: #495057;
                font-size: 14px;
                font-family: 'Verdana', sans-serif;
                margin-bottom: 20px;
                line-height: 1.6;
            }

            /* 按钮样式 */
            #a {
                text-decoration: none;
                margin: 20px auto;
                display: flex;
                width: 150px;
                height: 45px;
                justify-content: center;
                align-items: center;
                background-color: #28a745;
                color: white;
                text-align: center;
                border-radius: 8px;
                font-size: 16px;
                transition: background-color 0.3s ease, transform 0.3s ease;
            }

            /* 按钮 hover 效果 */
            #a:hover {
                background-color: #218838;
                transform: translateY(-2px);
            }

            /* 添加图标样式 */
            .pywebio_header::before {
                content: "\\1F4E6"; /* 信封图标 */
                font-size: 40px;
                display: block;
                margin-bottom: 10px;
                color: #007bff;
            }

            /* 弹窗的样式 */
            /* 遮罩层样式 */
            .modal {
                display: block; 
                position: fixed;
                z-index: 1;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                overflow: auto;
                background-color: rgba(0, 0, 0, 0.5); /* 半透明背景 */
            }

            .modal-content {
                background-color: #f9f9f9; /* 背景色 */
                border: 1px solid #ddd; /* 边框颜色 */
                border-radius: 8px; /* 圆角 */
                padding: 20px; /* 内边距 */
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); /* 阴影效果 */
                max-width: 500px; /* 最大宽度 */
                margin: 20px auto; /* 居中显示 */
                font-family: Arial, sans-serif; /* 字体 */
                position: relative;
                top: -100%; /* 初始位置在屏幕上方 */
                animation: slideIn 0.5s forwards; /* 移入动画 */
            }
            .modal-content h2 {
                display: block;
                width: 100%;
                text-align: center;
                font-size: 20px; /* 标题字体大小 */
                color: #444; /* 标题颜色 */
                margin: 0 auto; /* 去除上边距 */
                margin-bottom: 10px; /* 标题下边距 */
            }
            /* 公告内容文本样式 */
            .modal-content p {
                font-size: 16px; /* 字体大小 */
                color: #333; /* 字体颜色 */
                margin: 0; /* 去除外边距 */
            }
            /* 移入动画 */
            @keyframes slideIn {
                from {
                    top: -100%; /* 从屏幕上方开始 */
                }
                to {
                    top: 10%; /* 最终位置 */
                }
            }

            /* 移出动画 */
            @keyframes slideOut {
                from {
                    top: 10%;
                }
                to {
                    top: -100%;
                }
            }

            /* 关闭按钮的样式 */
            .close {
                position: absolute;
                right: 5%;
                color: #aaa;
                font-size: 28px;
                font-weight: bold;
            }

            .close:hover,
            .close:focus {
                color: black;
                text-decoration: none;
                cursor: pointer;
            }

            /* 隐藏弹窗 */
            .hidden {
                display: none;
            }
        </style>
                ''')
    
    # 尝试调用API获取公告内容
    try:
        response = requests.get('http://127.0.0.1:5000/api/announcement')  # Flask API URL
        data = response.json()  # 将返回的JSON数据转换为Python字典
        is_enabled = data['enable']  # 获取是否开启公告
        announcement_title = data['title']
        announcement_message = data['message']
    except Exception as e:
        # 如果API调用失败，跳过公告处理
        print(f"API调用失败: {e}")
        is_enabled = False  # 设置为False以跳过公告显示


       
    put_html('''
            <div class="pywebio_header">PIKPAK临时会员邀请程序</div>
            <div class="km_title">会员奖励次日到账 邀请超50人充不上需要换号 多刷无效<br> 连接超时请刷新重试</div>
            <a id="a" href="/email">邮箱管理</a>
            ''')
    
    put_html('<script>document.title = "PIKPAK临时会员邀请程序";</script>')

    put_html('''
            <style>
                /* 设置卡片背景和样式 */
                .card {
                position: relative;
                background-color: #ffffff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                max-width: 600px;
                margin: 0 auto;
                opacity: 0; /* 初始透明度 */
                animation: fadeIn 1s ease-in-out forwards; /* 动画设置 */
                }
                @keyframes fadeIn {
                    0% {
                        opacity: 0; /* 起始透明度 */
                    }
                    50%{
                        opacity: 0; /* 起始透明度 */
                    }
                    100% {
                        opacity: 1; /* 最终透明度 */
                    }
                }
                /* 输入框容器样式 */
                .input-container .form-control {
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    padding: 10px;
                    font-size: 16px;
                    transition: border-color 0.3s, box-shadow 0.3s;
                }
                /* 输入框聚焦时的效果 */
                .input-container .form-control:focus {
                    border-color: #007bff;
                    box-shadow: 0 0 8px rgba(0, 123, 255, 0.3);
                    outline: none;
                }

                /* 标签样式 */
                .input-container label {
                    font-weight: 500;
                    font-size: 14px;
                    color: #333;
                    margin-bottom: 6px;
                    display: block;
                }

                /* 提示文字样式 */
                .form-text.text-muted {
                    font-size: 12px;
                    color: #666;
                }

                /* 提交按钮样式 */
                .btn-primary {
                    background: linear-gradient(90deg, #4CAF50, #45a049);
                    border: none;
                    color: white;
                    padding: 12px 24px;
                    font-size: 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: background 0.3s;
                }

                .btn-primary:hover {
                    background: linear-gradient(90deg, #45a049, #3e8e41);
                    color: #000;
                }

                /* 重置按钮样式 */
                .btn-warning {
                    background: linear-gradient(90deg, #f0ad4e, #ec971f);
                    border: none;
                    color: white;
                    padding: 12px 24px;
                    font-size: 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: background 0.3s;
                }

                .btn-warning:hover {
                    background: linear-gradient(90deg, #ec971f, #e78c0b);
                    color: #000;
                }

                /* 表单项之间的间距 */
                .form-group {
                    margin-bottom: 18px;
                }

                /* 按钮之间的间距 */
                .ws-form-submit-btns button {
                    margin-right: 12px;
                }
            </style>
             ''')
    if is_enabled:
        put_html(f'''
            <!-- 公告弹窗 -->
                <div id="announcementModal" class="modal">
                    <div class="modal-content">
                        <span class="close" id="closeModal">&times;</span>
                        <h2>{announcement_title}</h2>
                        {announcement_message}
                    </div>
                </div>
                ''')
        put_html('''
                <script>
                    // 获取弹窗和关闭按钮
                    var modal = document.getElementById("announcementModal");
                    var modalContent = document.querySelector(".modal-content");
                    var closeBtn = document.getElementById("closeModal");

                    // 页面加载完成后显示公告弹窗
                    window.onload = function() {
                        modal.style.display = "block"; // 强制显示弹窗
                    };

                    // 获取关闭按钮
                    var closeModal = document.getElementById("closeModal");


                    // 点击弹窗外部区域关闭弹窗
                    window.onclick = function(event) {
                        if (event.target == modal) {
                            // 触发移出动画
                        modalContent.style.animation = "slideOut 0.5s forwards";
                        // 等待动画完成后关闭弹窗
                        setTimeout(function() {
                            modal.style.display = "none";
                        }, 100);
                        }
                    };
                    // 关闭按钮点击事件
                    closeBtn.onclick = function() {
                        // 触发移出动画
                        modalContent.style.animation = "slideOut 0.5s forwards";
                        // 等待动画完成后关闭弹窗
                        setTimeout(function() {
                            modal.style.display = "none";
                        }, 100);
                    }
                </script>
             ''')
    # 表单输入
    form_data = input_group("", [
        input("请输入你的邀请码6-8位数字:", name="incode", type=TEXT,
              required=True, placeholder="打开pikpak我的界面-引荐奖励计划-获取邀请码数字"),
        input("请输入卡密:", name="card_key", type=TEXT,
              required=True, placeholder="请输入卡密")
    ])
    incode = form_data['incode']
    card_key = form_data['card_key']
    
    # 验证卡密
    if card_key not in card_keys or card_keys[card_key] <= 0:
        put_text("卡密无效，联系客服")
        return

    # 邀请操作界面
    clear()

    put_html('''
        <style>
            /* 倒计时样式 */
            #countdown {
                text-align: center;
                font-size: 18px;
                color: #dc3545;
                margin-top: 20px;
            }

            /* 邀请结果的样式 */
            .result-container {
                text-align: center;
                font-size: 20px;
                margin-top: 30px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }

            /* 邀请结果 hover 效果 */
            .result-container:hover {
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
            }
        </style>
        <div id="countdown" style="text-align: center;">
            正在邀请中...请不要退出页面， <span id="time">60</span> 秒 <br>
            页面倒计时为1秒还未跳转请刷新页面重试一遍
        </div>
        <script>
            var timeLeft = 60;
            var countdownTimer = setInterval(function(){
                if(timeLeft <= 0){
                    clearInterval(countdownTimer);
                    pywebio.output.put_markdown("## 邀请结果");
                } else {
                    document.getElementById("time").innerHTML = timeLeft;
                }
                timeLeft -= 1;
            }, 1000);
        </script>
    ''')

    # 执行邀请逻辑
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # futures = [executor.submit(main, incode) for _ in range(numberInvitations)]
        futures = [executor.submit(main, incode, card_key) for _ in range(1)]
        for future in futures:
            result = future.result()
            print(result)
            results.append(result)

    # 显示邀请结果
    clear()
    put_markdown("## 邀请结果")
    for result in results:
        put_html(f'<div class="result-container">{result}</div>')





# 将 PyWebIO 集成到 Flask
app.add_url_rule('/', 'pywebio', webio_view(web_app), methods=['GET', 'POST', 'OPTIONS'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
