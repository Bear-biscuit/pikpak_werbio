import os
import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
import poplib
import hashlib
import json
import random
import re
import logging
import time
import requests
import uuid
import email
import threading
from pywebio.input import input_group, input, TEXT
from pywebio.output import put_text, put_markdown, clear, put_html
from pywebio import start_server
# from datetime import datetime
from pywebio.platform.flask import webio_view

app = Flask(__name__)
# 创建一个自定义日志过滤器
class RequestFilter(logging.Filter):
    def filter(self, record):
        
        if '/?app=index' in record.getMessage():
            return False  
        return True  

# 获取Flask默认的日志记录器
log = logging.getLogger('werkzeug')

# 添加过滤器到日志记录器
log.addFilter(RequestFilter())

# -------------改这里-------------
# r'替换为自己txt文件所在地址'
file_path = r'./email.txt'

# 卡密文件路径
card_keys_file = r'./card_keys.json'

# 公告内容文件
JSON_FILE_PATH = r'./announcement.json'

# 读取公告
def read_announcements():
    if not os.path.exists(JSON_FILE_PATH):
        return []
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (IOError, json.JSONDecodeError) as e:
        print(f"读取公告时发生错误: {e}")
        data = []
    return data
# 保存公告
def save_announcements(data):
    try:
        with open(JSON_FILE_PATH, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"保存公告时发生错误: {e}")


# 提供指定ID公告的API
@app.route('/api/announcement/<int:announcement_id>', methods=['GET'])
def api_announcement_detail(announcement_id):
    announcements = read_announcements()
    
    # 根据ID查找公告
    announcement = next((a for a in announcements if a['id'] == announcement_id), None)
    
    if announcement:
        return jsonify(announcement)
    else:
        # 如果找不到公告，返回404状态码和JSON格式的错误消息
        return jsonify({'error': '公告未找到'}), 404

# 提供当前启用的公告API
@app.route('/api/announcement/active', methods=['GET'])
def api_active_announcement():
    announcements = read_announcements()
    
    # 查找启用的公告
    active_announcement = next((a for a in announcements if a['enable']), None)
    
    if active_announcement:
        return jsonify(active_announcement)
    else:
        # 如果没有启用的公告，返回404
        return jsonify({'error': '没有启用的公告'}), 404

@app.route('/delete_announcement/<int:announcement_id>', methods=['POST'])
def delete_announcement(announcement_id):
    announcements = read_announcements()

    # 查找并删除公告
    updated_announcements = [a for a in announcements if a['id'] != announcement_id]

    # 如果删除后公告数量减少，则保存更新后的公告列表
    if len(updated_announcements) < len(announcements):
        save_announcements(updated_announcements)
        flash('公告已删除', 'success')
    else:
        flash('未找到该公告', 'error')

    return redirect(url_for('edit_announcement'))





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


initialized = False
# 首页路径 email 
@app.route('/email')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    global initialized
    if not initialized:
        write_status({
            'detection_active': False,
            'interval': 600,
            'next_check': 0
        })
        initialized = True
    emails = read_emails()
    return render_template('index.html', emails=emails)

# 公告编辑页面
@app.route('/edit_announcement', methods=['GET', 'POST'])
def edit_announcement():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # 读取所有公告
    announcements = read_announcements()

    if request.method == 'POST':
        # 获取表单数据
        announcement_id = int(request.form.get('announcement_id', -1))
        enable = request.form.get('enable') == 'on'
        title = request.form.get('title')
        message = request.form.get('message')  # HTML富文本公告内容

        # 如果一个公告被启用，禁用其他公告
        if enable:
            for announcement in announcements:
                announcement['enable'] = False

        if announcement_id == -1:
            # 添加新的公告
            new_id = max([a['id'] for a in announcements], default=0) + 1
            announcements.append({
                "id": new_id,
                "enable": enable,
                "title": title,
                "message": message
            })
        else:
            # 更新现有公告
            for announcement in announcements:
                if announcement['id'] == announcement_id:
                    announcement.update({
                        "enable": enable,
                        "title": title,
                        "message": message
                    })
                    break

        # 保存更新后的公告列表
        save_announcements(announcements)
        flash('保存成功', 'success')
        return redirect(url_for('edit_announcement'))

    # 如果是GET请求，读取所有公告并显示
    return render_template('edit_announcement.html', announcements=announcements)


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
                    fixed_password = fixed_password = account_info[1].split(' ')[0]  # 只获取密码
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
                    updated_line = f"{email}----{password} {status} {time}\n"
                    file.write(updated_line)
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
    # proxy_uri = requests.get('https://www.example.com/fetch_random').text
    proxy_uri = requests.get('https://proxy.bocchi2b.top/fetch_random').text
    
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



def get_sign(orgin_str, salts):
    for salt in salts:
        orgin_str = get_hash(orgin_str + salt["salt"])
    return orgin_str

# 安全验证
def init(client_id, captcha_token, device_id, User_Agent, action, meta):
    # print(meta)
    retries = 1
    max_retries = 3
    url = "https://user.mypikpak.com/v1/shield/captcha/init"

    querystring = {"client_id": client_id}

    payload = {
        "action": action,
        "captcha_token": captcha_token,
        "client_id": client_id,
        "device_id": device_id,
        "meta": meta,
        "redirect_uri": "xlaccsdk01://xbase.cloud/callback?state=harbor"
    }
    # print(meta)
    headers = {
        "X-Device-Id": device_id,
        "User-Agent": User_Agent,
    }
    headers.update(basicRequestHeaders_1)
    proxy = get_proxy()
    print('获取到的代理是', proxy)
    while retries < max_retries:
        try:
            response = requests.request("POST", url, json=payload, headers=headers, params=querystring, proxies=proxy, timeout=5)
            response_data = response.json()
            print(response.json())
            return response_data
        except:
            print('安全验证失败',retries,'次')
            retries += 1
    print('连接超时')
    return '连接超时'
# 二次安全验证
def init1(client_id, captcha_token, device_id, User_Agent, action, meta):
    # print(meta)
    retries = 1
    max_retries = 4
    url = "https://user.mypikpak.com/v1/shield/captcha/init"

    querystring = {"client_id": client_id}

    payload = {
        "action": action,
        "captcha_token": captcha_token,
        "client_id": client_id,
        "device_id": device_id,
        "meta": meta,
        "redirect_uri": "xlaccsdk01://xbase.cloud/callback?state=harbor"
    }
    # print(meta)
    headers = {
        "X-Device-Id": device_id,
        "User-Agent": User_Agent,
    }
    headers.update(basicRequestHeaders_1)
    while retries < max_retries:
        try:
            response = requests.request("POST", url, json=payload, headers=headers, params=querystring, timeout=5)
            response_data = response.json()
            print(response.json())
            return response_data
        except:
            print('安全验证失败',retries,'次')
            retries += 1
    print('连接超时')
    return '连接超时'
# 发送验证码
def verification(client_id, captcha_token, email, device_id, User_Agent):
    url = "https://user.mypikpak.com/v1/auth/verification"

    querystring = {"client_id": client_id}

    payload = {
        "captcha_token": captcha_token,
        "email": email,
        "locale": "zh-CN",
        "target": "ANY",
        "client_id": client_id
    }
    headers = {
        "X-Device-Id": device_id,
        "User-Agent": User_Agent,
    }
    headers.update(basicRequestHeaders_1)
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.request("POST", url, json=payload, headers=headers, params=querystring, timeout=5)
            response_data = response.json()
            print('发送验证码')
            return response_data
        except:
            retries += 1
    

    print('发送验证码失败')


# 验证码结果
def verify(client_id, verification_id, verification_code, device_id, User_Agent):
    url = "https://user.mypikpak.com/v1/auth/verification/verify"

    querystring = {"client_id": client_id}

    payload = {
        "client_id": client_id,
        "verification_id": verification_id,
        "verification_code": verification_code
    }
    headers = {
        "X-Device-Id": device_id,
        "User-Agent": User_Agent,
    }
    headers.update(basicRequestHeaders_1)
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.request("POST", url, json=payload, headers=headers, params=querystring, timeout=5)
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
def signup(client_id, captcha_token, client_secret, email, name, password, verification_token, device_id, User_Agent):
    url = "https://user.mypikpak.com/v1/auth/signup"

    querystring = {"client_id": client_id}

    payload = {
        "captcha_token": captcha_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "email": email,
        "name": name,
        "password": password,
        "verification_token": verification_token
    }
    headers = {
        "X-Device-Id": device_id,
        "User-Agent": User_Agent,
    }
    headers.update(basicRequestHeaders_1)
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.request("POST", url, json=payload, headers=headers, params=querystring,timeout=5)
            response_data = response.json()
            print('验证注册结果')
            return response_data
        except:
            retries += 1



# 确认邀请
def invite(user_id, phoneModel, phoneBuilder, invite_code, captcha_token, device_id, access_token, User_Agent,
           version):
    url = 'https://api-drive.mypikpak.com/vip/v1/activity/invite'
    payload = {
        "data": {
            "sdk_int": "33",
            "uuid": device_id,
            "userType": "1",
            "userid": user_id,
            "userSub": "",
            "product_flavor_name": "cha",
            "language_system": "zh-CN",
            "language_app": "zh-CN",
            "build_version_release": "13",
            "phoneModel": phoneModel,
            "build_manufacturer": phoneBuilder,
            "build_sdk_int": "33",
            "channel": "official",
            "versionCode": "10150",
            "versionName": version,
            "installFrom": "other",
            "country": "PL"
        },
        "apk_extra": {"channel": "official"}
    }
    headers = {
        "Host": "api-drive.mypikpak.com",
        "authorization": "Bearer " + access_token,
        "product_flavor_name": "cha",
        "x-captcha-token": captcha_token,
        "x-client-version-code": "10150",
        "x-device-id": device_id,
        "user-agent": User_Agent,
        "country": "PL",
        "accept-language": "zh-CN",
        "x-peer-id": device_id,
        "x-user-region": "2",
        "x-system-language": "zh-CN",
        "x-alt-capability": "3",
        "accept-encoding": "gzip",
        "content-type": "application/json"
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.request("POST", url, json=payload, headers=headers, timeout=5)
            response_data = response.json()
            print('确认邀请')
            return response_data
        except:
            retries += 1



# 验证邀请码
def activation_code(user_id, phoneModel, phoneBuilder, invite_code, captcha_token, device_id, access_token, User_Agent):
    url = "https://api-drive.mypikpak.com/vip/v1/order/activation-code"

    payload = {"activation_code": invite_code}
    headers = {
        "Host": "api-drive.mypikpak.com",
        "authorization": "Bearer " + access_token,
        "product_flavor_name": "cha",
        "x-captcha-token": captcha_token,
        "x-client-version-code": "10150",
        "x-device-id": device_id,
        "user-agent": User_Agent,
        "country": "DK",
        "accept-language": "zh-CN",
        "x-peer-id": device_id,
        "x-user-region": "2",
        "x-system-language": "zh-CN",
        "x-alt-capability": "3",
        "content-length": "30",
        "accept-encoding": "gzip",
        "content-type": "application/json"
    }
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = requests.request("POST", url, json=payload, headers=headers,timeout=5)
            response_data = response.json()
            print('开始填写邀请码')
            # print(f'邀请结果:  {json.dumps(response_data, indent=4)}')
            return response_data
        except:
            retries += 1

# -------------------------- 邮箱保活部分--------------------------
# 全局变量用于控制检测任务的开启和关闭
detection_active = False
detection_thread = None
detection_event = threading.Event()  # 用于检测任务是否完成 
STATUS_FILE = 'status.json'
file_lock = threading.Lock()
# 读取txt文件并显示调试信息
def read_status():
    try:
        if os.path.getsize(STATUS_FILE) == 0:  # 检查文件是否为空
            raise ValueError("JSON file is empty")
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise ValueError("JSON file contains invalid data")
    except Exception as e:
        raise ValueError(f"Error reading status file: {str(e)}")

def write_status(data):
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error writing status file: {str(e)}")




@app.route('/get_status')
def get_status():
    try:
        status = read_status()
        return jsonify(status)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400



def read_email_file(file_path):
    accounts = []
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        print(f"读取到 {len(lines)} 行内容")
        for line in lines:
            line = line.strip()
            if ' 登录成功' in line or ' 失败' in line:
                print(f"跳过处理已标记的行: {line}")
            else:
                parts = line.split('----')
                if len(parts) == 2:
                    email = parts[0]
                    password = parts[1]
                    # print(f"准备检测邮箱: {email}")
                    accounts.append({'line': line, 'email': email, 'password': password, 'status': ''})
                else:
                    print(f"跳过无法解析的行: {line}")
    return accounts

# 尝试通过POP3登录邮箱，并动态检测是否需要停止
def check_email_login(account):
    global detection_active
    email = account['email']
    password = account['password']
    
    retries = 2
    for attempt in range(1, retries + 1):
        if not detection_active:
            # print(f"检测中断，邮箱 {email} 未检测")
            return email, "检测中断"
        
        try:
            # print(f"正在尝试第 {attempt} 次登录: {email}")
            server = poplib.POP3_SSL('pop-mail.outlook.com', 995)
            server.user(email)
            server.pass_(password)
            server.quit()
            # print(f"邮箱 {email} 登录成功")
            return email, "登录成功"
        except poplib.error_proto as e:
            if b'-ERR Logon failure: unknown user name or bad password.' in str(e).encode():
                # print(f"邮箱 {email} 登录失败: {str(e)}，直接删除")
                return email, "删除"
            # print(f"邮箱 {email} 第 {attempt} 次尝试登录失败: {str(e)}")
            if attempt == retries:
                return email, "删除"

# 实时更新txt文件
def update_file_line(file_path, account):
    with file_lock:
        with open(file_path, 'r+', encoding='utf-8') as file:
            lines = file.readlines()
            if account['status'] == '登录成功':
                for i, line in enumerate(lines):
                    if account['email'] in line and account['password'] in line:
                        lines[i] = account['line'] + '\n'
                        break
            elif account['status'] == '删除':
                lines = [line for line in lines if account['email'] not in line and account['password'] not in line]
            file.seek(0)
            file.writelines(lines)
            file.truncate()
            # print(f"文件 {file_path} 已更新")


# 获取CPU核心数并设置合理的线程数量
max_workers = os.cpu_count() * 2
# 多线程检测邮箱登录
def check_emails_multithread(accounts, file_path, max_workers):
    global detection_active
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_email_login, account): account for account in accounts}
        print(f"开始多线程检测，共 {len(futures)} 个任务")
        
        for future in as_completed(futures):
            account = futures[future]
            try:
                email, result = future.result()
                account['status'] = result
                if detection_active:
                    update_file_line(file_path, account)
            except Exception as e:
                print(f"处理邮箱 {account['email']} 时发生异常: {str(e)}")
    
    # 所有多线程任务执行完毕后的提示
    print("所有多线程任务已完成")

# 定时检测任务
def email_detection_task(interval, file_path):
    global detection_active
    while detection_active:
        print("开始邮箱检测...")
        detection_event.clear()
        check_emails_multithread(read_email_file(file_path), file_path, max_workers)
        detection_event.set()
        next_check_time = time.time() + interval
        write_status({
            'detection_active': detection_active,
            'interval': interval,
            'next_check': next_check_time
        })
        time.sleep(interval)



@app.route('/toggle_detection', methods=['POST'])
def toggle_detection():
    global detection_active, detection_thread
    action = request.json.get('action')
    interval = int(request.json.get('interval', 600))  # 默认间隔为10分钟（600秒）

    if action == 'start' and not detection_active:
        detection_active = True
        detection_thread = threading.Thread(target=email_detection_task, args=(interval, 'email.txt'))
        detection_thread.start()
        # 更新状态文件
        next_check_time = time.time() + interval
        write_status({
            'detection_active': detection_active,
            'interval': interval,
            'next_check': next_check_time
        })
        return jsonify({'status': 'started'})
    
    elif action == 'stop' and detection_active:
        detection_active = False
        detection_event.set()  # 触发事件，通知任务停止
        if detection_thread:
            detection_thread.join(timeout=5)  # 等待最多5秒
        # 更新状态文件
        write_status({
            'detection_active': detection_active,
            'interval': interval,
            'next_check': 0  # 停止检测时，下次检查时间设为0
        })
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'error'})
# --------------------------  基础信息  ------------------------------------
# 设置请求头基本信息
basicRequestHeaders_1 = {
    "Accept-Language": "zh",
    "Content-Type": "application/json; charset=utf-8",
    "Host": "user.mypikpak.com",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "content-type": "application/json"
}

basicRequestHeaders_2 = {
    "x-requested-with": "com.pikcloud.pikpak",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "accept-encoding": "gzip, deflate",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "cookie": "mainHost=user.mypikpak.com"
}
# UA表，随机信息采集
uaList = [{'model': 'MI-ONE PLUS', 'name': ' 小米 1 联通版'}, {'model': 'MI-ONE C1', 'name': ' 小米 1 电信版'},
          {'model': 'MI-ONE', 'name': ' 小米 1 青春版'}, {'model': '2012051', 'name': ' 小米 1S 联通版'},
          {'model': '2012053', 'name': ' 小米 1S 电信版'}, {'model': '2012052', 'name': ' 小米 1S 青春版'},
          {'model': '2012061', 'name': ' 小米 2 联通版'}, {'model': '2012062', 'name': ' 小米 2 电信版'},
          {'model': '2013012', 'name': ' 小米 2S 联通版'}, {'model': '2013021', 'name': ' 小米 2S 电信版'},
          {'model': '2012121', 'name': ' 小米 2A 联通版'}, {'model': '2013061', 'name': ' 小米 3 移动版'},
          {'model': '2013062', 'name': ' 小米 3 联通版'}, {'model': '2013063', 'name': ' 小米 3 电信版'},
          {'model': '2014215', 'name': ' 小米 4 联通 3G 版'}, {'model': '2014218', 'name': ' 小米 4 电信 3G 版'},
          {'model': '2014216', 'name': ' 小米 4 移动 4G 版'}, {'model': '2014719', 'name': ' 小米 4 联通 4G 版'},
          {'model': '2014716', 'name': ' 小米 4 电信 4G 版'}, {'model': '2014726', 'name': ' 小米 4 电信 4G 合约版'},
          {'model': '2015015', 'name': ' 小米 4i 国际版'}, {'model': '2015561', 'name': ' 小米 4c 全网通版'},
          {'model': '2015562', 'name': ' 小米 4c 移动合约版'}, {'model': '2015911', 'name': ' 小米 4S 全网通版'},
          {'model': '2015201', 'name': ' 小米 5 标准版'}, {'model': '2015628', 'name': ' 小米 5 高配版 / 尊享版'},
          {'model': '2015105', 'name': ' 小米 5 国际版'}, {'model': '2015711', 'name': ' 小米 5s 全网通版'},
          {'model': '2016070', 'name': ' 小米 5s Plus 全网通版'}, {'model': '2016089', 'name': ' 小米 5c 移动版'},
          {'model': 'MDE2', 'name': ' 小米 5X 全网通版'}, {'model': 'MDT2', 'name': ' 小米 5X 移动 4G+ 版'},
          {'model': 'MCE16', 'name': ' 小米 6 全网通版'}, {'model': 'MCT1', 'name': ' 小米 6 移动 4G+ 版'},
          {'model': 'M1804D2SE', 'name': ' 小米 6X 全网通版'}, {'model': 'M1804D2ST', 'name': ' 小米 6X 移动 4G+ 版'},
          {'model': 'M1804D2SC', 'name': ' 小米 6X 联通电信定制版'}, {'model': 'M1803E1A', 'name': ' 小米 8 全网通版'},
          {'model': 'M1803E1T', 'name': ' 小米 8 移动 4G+ 版'}, {'model': 'M1803E1C', 'name': ' 小米 8 联通电信定制版'},
          {'model': 'M1807E8S', 'name': ' 小米 8 透明探索版'}, {'model': 'M1807E8A', 'name': ' 小米 8 屏幕指纹版'},
          {'model': 'M1805E2A', 'name': ' 小米 8 SE 全网通版'},
          {'model': 'M1808D2TE', 'name': ' 小米 8 青春版 全网通版'},
          {'model': 'M1808D2TT', 'name': ' 小米 8 青春版 移动 4G+ 版'},
          {'model': 'M1808D2TC', 'name': ' 小米 8 青春版 联通电信定制版'},
          {'model': 'M1808D2TG', 'name': ' 小米 8 Lite 国际版'}, {'model': 'M1902F1A', 'name': ' 小米 9 全网通版'},
          {'model': 'M1902F1T', 'name': ' 小米 9 移动 4G+ 版'}, {'model': 'M1902F1C', 'name': ' 小米 9 联通电信定制版'},
          {'model': 'M1902F1G', 'name': ' 小米 9 国际版'}, {'model': 'M1908F1XE', 'name': ' 小米 9 Pro 5G 全网通版'},
          {'model': 'M1903F2A', 'name': ' 小米 9 SE 全网通版'}, {'model': 'M1903F2G', 'name': ' 小米 9 SE 国际版'},
          {'model': 'M1903F10G', 'name': ' 小米 9T 国际版'}, {'model': 'M1903F11G', 'name': ' 小米 9T Pro 国际版'},
          {'model': 'M1904F3BG', 'name': ' 小米 9 Lite 国际版'},
          {'model': 'M2001J2E M2001J2C', 'name': ' 小米 10 全网通版'}, {'model': 'M2001J2G', 'name': ' 小米 10 国际版'},
          {'model': 'M2001J2I', 'name': ' 小米 10 印度版'},
          {'model': 'M2001J1E M2001J1C', 'name': ' 小米 10 Pro 全网通版'},
          {'model': 'M2001J1G', 'name': ' 小米 10 Pro 国际版'},
          {'model': 'M2002J9E', 'name': ' 小米 10 青春版 全网通版'},
          {'model': 'M2002J9G', 'name': ' 小米 10 Lite 国际版'}, {'model': 'M2002J9S', 'name': ' 小米 10 Lite 韩国版'},
          {'model': 'M2002J9R XIG01', 'name': ' 小米 10 Lite 日本版 (KDDI)'},
          {'model': 'M2007J1SC', 'name': ' 小米 10 至尊纪念版 全网通版'},
          {'model': 'M2007J3SY', 'name': ' 小米 10T 国际版'}, {'model': 'M2007J3SP', 'name': ' 小米 10T 印度版'},
          {'model': 'M2007J3SG', 'name': ' 小米 10T Pro 国际版'},
          {'model': 'M2007J3SI', 'name': ' 小米 10T Pro 印度版'},
          {'model': 'M2007J17G', 'name': ' 小米 10T Lite 国际版'}, {'model': 'M2007J17I', 'name': ' 小米 10i 印度版'},
          {'model': 'M2102J2SC', 'name': ' 小米 10S 全网通版'}, {'model': 'M2011K2C', 'name': ' 小米 11 全网通版'},
          {'model': 'M2011K2G', 'name': ' 小米 11 国际版'}, {'model': 'M2102K1AC', 'name': ' 小米 11 Pro 全网通版'},
          {'model': 'M2102K1C', 'name': ' 小米 11 Ultra 全网通版'},
          {'model': 'M2102K1G', 'name': ' 小米 11 Ultra 国际版'},
          {'model': 'M2101K9C', 'name': ' 小米 11 青春版 全网通版'},
          {'model': 'M2101K9G', 'name': ' 小米 11 Lite 5G 国际版'},
          {'model': 'M2101K9R', 'name': ' 小米 11 Lite 5G 日本版'},
          {'model': 'M2101K9AG', 'name': ' 小米 11 Lite 4G 国际版'},
          {'model': 'M2101K9AI', 'name': ' 小米 11 Lite 4G 印度版'},
          {'model': '2107119DC', 'name': ' Xiaomi 11 青春活力版 全网通版'},
          {'model': '2109119DG', 'name': ' Xiaomi 11 Lite 5G NE 国际版'},
          {'model': '2109119DI', 'name': ' Xiaomi 11 Lite NE 5G 印度版'},
          {'model': 'M2012K11G', 'name': ' 小米 11i 国际版'}, {'model': 'M2012K11AI', 'name': ' 小米 11X 印度版'},
          {'model': 'M2012K11I', 'name': ' 小米 11X Pro 印度版'}, {'model': '21081111RG', 'name': ' Xiaomi 11T 国际版'},
          {'model': '2107113SG', 'name': ' Xiaomi 11T Pro 国际版'},
          {'model': '2107113SI', 'name': ' Xiaomi 11T Pro 印度版'},
          {'model': '2107113SR', 'name': ' Xiaomi 11T Pro 日本版'},
          {'model': '21091116I', 'name': ' Xiaomi 11i 印度版'},
          {'model': '21091116UI', 'name': ' Xiaomi 11i HyperCharge 印度版'},
          {'model': '2201123C', 'name': ' Xiaomi 12 全网通版'}, {'model': '2201123G', 'name': ' Xiaomi 12 国际版'},
          {'model': '2112123AC', 'name': ' Xiaomi 12X 全网通版'}, {'model': '2112123AG', 'name': ' Xiaomi 12X 国际版'},
          {'model': '2201122C', 'name': ' Xiaomi 12 Pro 全网通版'},
          {'model': '2201122G', 'name': ' Xiaomi 12 Pro 国际版'},
          {'model': '2207122MC', 'name': ' Xiaomi 12 Pro 天玑版 全网通版'},
          {'model': '2203129G', 'name': ' Xiaomi 12 Lite 国际版'},
          {'model': '2203129I', 'name': ' Xiaomi 12 Lite 印度版'},
          {'model': '2206123SC', 'name': ' Xiaomi 12S 全网通版'},
          {'model': '2206122SC', 'name': ' Xiaomi 12S Pro 全网通版'},
          {'model': '2203121C', 'name': ' Xiaomi 12S Ultra 全网通版'},
          {'model': '22071212AG', 'name': ' Xiaomi 12T 国际版'},
          {'model': '22081212UG', 'name': ' Xiaomi 12T Pro 国际版'},
          {'model': '22081212R 22200414R', 'name': ' Xiaomi 12T Pro 日本版 (SIM Free)'},
          {'model': 'A201XM', 'name': ' Xiaomi 12T Pro 日本版 (SoftBank)'},
          {'model': '2211133C', 'name': ' Xiaomi 13 全网通版'}, {'model': '2211133G', 'name': ' Xiaomi 13 国际版'},
          {'model': '2210132C', 'name': ' Xiaomi 13 Pro 全网通版'},
          {'model': '2210132G', 'name': ' Xiaomi 13 Pro 国际版'},
          {'model': '2304FPN6DC', 'name': ' Xiaomi 13 Ultra 全网通版'},
          {'model': '2304FPN6DG', 'name': ' Xiaomi 13 Ultra 国际版'},
          {'model': '2210129SG', 'name': ' Xiaomi 13 Lite 国际版'},
          {'model': '2306EPN60G', 'name': ' Xiaomi 13T 国际版'}, {'model': '2306EPN60R', 'name': ' Xiaomi 13T 日本版'},
          {'model': '23078PND5G', 'name': ' Xiaomi 13T Pro 国际版'},
          {'model': '2014616', 'name': ' 小米 Note 双网通版'}, {'model': '2014619', 'name': ' 小米 Note 全网通版'},
          {'model': '2014618', 'name': ' 小米 Note 移动合约版'}, {'model': '2014617', 'name': ' 小米 Note 联通合约版'},
          {'model': '2015011', 'name': ' 小米 Note 国际版'}, {'model': '2015021', 'name': ' 小米 Note 顶配版 双网通版'},
          {'model': '2015022', 'name': ' 小米 Note 顶配版 全网通版'},
          {'model': '2015501', 'name': ' 小米 Note 顶配版 移动合约版'},
          {'model': '2015211', 'name': ' 小米 Note 2 全网通版'},
          {'model': '2015212', 'name': ' 小米 Note 2 移动 4G+ 版'},
          {'model': '2015213', 'name': ' 小米 Note 2 全网通版 (全球频段)'},
          {'model': 'MCE8', 'name': ' 小米 Note 3 全网通版'}, {'model': 'MCT8', 'name': ' 小米 Note 3 移动 4G+ 版'},
          {'model': 'M1910F4G', 'name': ' 小米 Note 10 国际版'},
          {'model': 'M1910F4S', 'name': ' 小米 Note 10 Pro 国际版'},
          {'model': 'M2002F4LG', 'name': ' 小米 Note 10 Lite 国际版'},
          {'model': '2016080', 'name': ' 小米 MIX 全网通版'},
          {'model': 'MDE5', 'name': ' 小米 MIX 2 黑色陶瓷版 全网通版'},
          {'model': 'MDT5', 'name': ' 小米 MIX 2 黑色陶瓷版 移动 4G+ 版'},
          {'model': 'MDE5S', 'name': ' 小米 MIX 2 全陶瓷尊享版'},
          {'model': 'M1803D5XE', 'name': ' 小米 MIX 2S 全网通版'},
          {'model': 'M1803D5XA', 'name': ' 小米 MIX 2S 尊享版 (全球频段)'},
          {'model': 'M1803D5XT', 'name': ' 小米 MIX 2S 移动 4G+ 版'},
          {'model': 'M1803D5XC', 'name': ' 小米 MIX 2S 联通电信定制版'},
          {'model': 'M1810E5E', 'name': ' 小米 MIX 3 全网通版'},
          {'model': 'M1810E5A', 'name': ' 小米 MIX 3 全网通版 (全球频段)'},
          {'model': 'M1810E5GG', 'name': ' 小米 MIX 3 5G'}, {'model': 'M2011J18C', 'name': ' MIX FOLD 小米折叠屏手机'},
          {'model': '2106118C', 'name': ' Xiaomi MIX 4'}, {'model': '22061218C', 'name': ' Xiaomi MIX Fold 2'},
          {'model': '2308CPXD0C', 'name': ' Xiaomi MIX Fold 3'},
          {'model': '2016001', 'name': ' 小米 Max 标准版 全网通版'},
          {'model': '2016002', 'name': ' 小米 Max 标准版 国际版'}, {'model': '2016007', 'name': ' 小米 Max 高配版'},
          {'model': 'MDE40', 'name': ' 小米 Max 2 全网通版'}, {'model': 'MDT4', 'name': ' 小米 Max 2 移动 4G+ 版'},
          {'model': 'MDI40', 'name': ' 小米 Max 2 印度版'}, {'model': 'M1804E4A', 'name': ' 小米 Max 3 全网通版'},
          {'model': 'M1804E4T', 'name': ' 小米 Max 3 移动 4G+ 版'},
          {'model': 'M1804E4C', 'name': ' 小米 Max 3 联通电信定制版'},
          {'model': 'M1904F3BC', 'name': ' 小米 CC9 全网通版'}, {'model': 'M1904F3BT', 'name': ' 小米 CC9 美图定制版'},
          {'model': 'M1906F9SC', 'name': ' 小米 CC9e 全网通版'},
          {'model': 'M1910F4E', 'name': ' 小米 CC9 Pro 全网通版'},
          {'model': '2109119BC', 'name': ' Xiaomi Civi 全网通版'},
          {'model': '2109119BC', 'name': ' Xiaomi Civi 1S 全网通版'},
          {'model': '2209129SC', 'name': ' Xiaomi Civi 2 全网通版'},
          {'model': '23046PNC9C', 'name': ' Xiaomi Civi 3 全网通版'},
          {'model': 'M1901F9E', 'name': ' 小米 Play 全网通版'}, {'model': 'M1901F9T', 'name': ' 小米 Play 移动 4G+ 版'},
          {'model': 'MDG2', 'name': ' 小米 A1 国际版'}, {'model': 'MDI2', 'name': ' 小米 A1 印度版'},
          {'model': 'M1804D2SG', 'name': ' 小米 A2 国际版'}, {'model': 'M1804D2SI', 'name': ' 小米 A2 印度版'},
          {'model': 'M1805D1SG', 'name': ' 小米 A2 Lite 国际版'}, {'model': 'M1906F9SH', 'name': ' 小米 A3 国际版'},
          {'model': 'M1906F9SI', 'name': ' 小米 A3 印度版'}, {'model': 'A0101', 'name': ' 小米平板'},
          {'model': '2015716', 'name': ' 小米平板 2'}, {'model': 'MCE91', 'name': ' 小米平板 3'},
          {'model': 'M1806D9W', 'name': ' 小米平板 4 Wi-Fi 版'}, {'model': 'M1806D9E', 'name': ' 小米平板 4 LTE 版'},
          {'model': 'M1806D9PE', 'name': ' 小米平板 4 Plus LTE 版'},
          {'model': '21051182C', 'name': ' 小米平板 5 国行版'}, {'model': '21051182G', 'name': ' 小米平板 5 国际版'},
          {'model': 'M2105K81AC', 'name': ' 小米平板 5 Pro Wi-Fi 版'},
          {'model': 'M2105K81C', 'name': ' 小米平板 5 Pro 5G'},
          {'model': '22081281AC', 'name': ' 小米平板 5 Pro 12.4 英寸'},
          {'model': '23043RP34C', 'name': ' Xiaomi Pad 6 国行版'},
          {'model': '23043RP34G', 'name': ' Xiaomi Pad 6 国际版'},
          {'model': '23043RP34I', 'name': ' Xiaomi Pad 6 印度版'}, {'model': '23046RP50C', 'name': ' Xiaomi Pad 6 Pro'},
          {'model': '2307BRPDCC', 'name': ' Xiaomi Pad 6 Max 14'}, {'model': '2013022', 'name': ' 红米手机 移动版'},
          {'model': '2013023', 'name': ' 红米手机 联通版'}, {'model': '2013029', 'name': ' 红米 1S 联通版'},
          {'model': '2013028', 'name': ' 红米 1S 电信版'}, {'model': '2014011', 'name': ' 红米 1S 移动 3G 版'},
          {'model': '2014501', 'name': ' 红米 1S 移动 4G 版'}, {'model': '2014813', 'name': ' 红米 2 移动版'},
          {'model': '2014112', 'name': ' 红米 2 移动合约版'}, {'model': '2014811', 'name': ' 红米 2 联通版'},
          {'model': '2014812', 'name': ' 红米 2 电信版'}, {'model': '2014821', 'name': ' 红米 2 电信合约版'},
          {'model': '2014817', 'name': ' 红米 2 国际版'}, {'model': '2014818', 'name': ' 红米 2 印度版'},
          {'model': '2014819', 'name': ' 红米 2 巴西版'}, {'model': '2014502', 'name': ' 红米 2A 标准版'},
          {'model': '2014512 2014055', 'name': ' 红米 2A 增强版'}, {'model': '2014816', 'name': ' 红米 2A 高配版'},
          {'model': '2015811 2015815', 'name': ' 红米 3 全网通 标准版'},
          {'model': '2015812', 'name': ' 红米 3 移动合约 标准版'},
          {'model': '2015810', 'name': ' 红米 3 联通合约 标准版'},
          {'model': '2015817 2015819', 'name': ' 红米 3 全网通 高配版'},
          {'model': '2015818', 'name': ' 红米 3 联通合约 高配版'}, {'model': '2015816', 'name': ' 红米 3 国际版'},
          {'model': '2016030', 'name': ' 红米 3S 全网通版'}, {'model': '2016031', 'name': ' 红米 3S 国际版'},
          {'model': '2016032', 'name': ' 红米 3S Prime 印度版'}, {'model': '2016037', 'name': ' 红米 3S 印度版'},
          {'model': '2016036', 'name': ' 红米 3X 全网通版'}, {'model': '2016035', 'name': ' 红米 3X 移动合约版'},
          {'model': '2016033', 'name': ' 红米 3X 全网通版 (联通定制)'}, {'model': '2016090', 'name': ' 红米 4 标准版'},
          {'model': '2016060', 'name': ' 红米 4 高配版'}, {'model': '2016111', 'name': ' 红米 4A 全网通版'},
          {'model': '2016112', 'name': ' 红米 4A 移动 4G+ 版'}, {'model': '2016117', 'name': ' 红米 4A 国际版'},
          {'model': '2016116', 'name': ' 红米 4A 印度版'}, {'model': 'MAE136', 'name': ' 红米 4X 全网通版'},
          {'model': 'MAT136', 'name': ' 红米 4X 移动 4G+ 版'}, {'model': 'MAG138', 'name': ' 红米 4X 国际版'},
          {'model': 'MAI132', 'name': ' 红米 4 印度版'}, {'model': 'MDE1', 'name': ' 红米 5 全网通版'},
          {'model': 'MDT1', 'name': ' 红米 5 移动 4G+ 版'}, {'model': 'MDG1', 'name': ' 红米 5 国际版'},
          {'model': 'MDI1', 'name': ' 红米 5 印度版'}, {'model': 'MEE7', 'name': ' 红米 5 Plus 全网通版'},
          {'model': 'MET7', 'name': ' 红米 5 Plus 移动 4G+ 版'}, {'model': 'MEG7', 'name': ' 红米 5 Plus 国际版'},
          {'model': 'MCE3B', 'name': ' 红米 5A 全网通版'}, {'model': 'MCT3B', 'name': ' 红米 5A 移动 4G+ 版'},
          {'model': 'MCG3B', 'name': ' 红米 5A 国际版'}, {'model': 'MCI3B', 'name': ' 红米 5A 印度版'},
          {'model': 'M1804C3DE', 'name': ' 红米 6 全网通版'}, {'model': 'M1804C3DT', 'name': ' 红米 6 移动 4G+ 版'},
          {'model': 'M1804C3DC', 'name': ' 红米 6 联通电信定制版'},
          {'model': 'M1804C3DG M1804C3DH', 'name': ' 红米 6 国际版'}, {'model': 'M1804C3DI', 'name': ' 红米 6 印度版'},
          {'model': 'M1805D1SE', 'name': ' 红米 6 Pro 全网通版'},
          {'model': 'M1805D1ST', 'name': ' 红米 6 Pro 移动 4G+ 版'},
          {'model': 'M1805D1SC', 'name': ' 红米 6 Pro 联通电信定制版'},
          {'model': 'M1805D1SI', 'name': ' 红米 6 Pro 印度版'}, {'model': 'M1804C3CE', 'name': ' 红米 6A 全网通版'},
          {'model': 'M1804C3CT', 'name': ' 红米 6A 移动 4G+ 版'},
          {'model': 'M1804C3CC', 'name': ' 红米 6A 联通电信定制版'},
          {'model': 'M1804C3CG M1804C3CH', 'name': ' 红米 6A 国际版'},
          {'model': 'M1804C3CI', 'name': ' 红米 6A 印度版'}, {'model': 'M1810F6LE', 'name': ' Redmi 7 全网通版'},
          {'model': 'M1810F6LT', 'name': ' Redmi 7 运营商全网通版'},
          {'model': 'M1810F6LG M1810F6LH', 'name': ' Redmi 7 国际版'},
          {'model': 'M1810F6LI', 'name': ' Redmi 7 印度版'}, {'model': 'M1903C3EE', 'name': ' Redmi 7A 全网通版'},
          {'model': 'M1903C3ET', 'name': ' Redmi 7A 移动 4G+ 版'},
          {'model': 'M1903C3EC', 'name': ' Redmi 7A 联通电信定制版'},
          {'model': 'M1903C3EG M1903C3EH', 'name': ' Redmi 7A 国际版'},
          {'model': 'M1903C3EI', 'name': ' Redmi 7A 印度版'}, {'model': 'M1908C3IE', 'name': ' Redmi 8 全网通版'},
          {'model': 'M1908C3IC', 'name': ' Redmi 8 运营商全网通版'},
          {'model': 'M1908C3IG M1908C3IH', 'name': ' Redmi 8 国际版'},
          {'model': 'M1908C3II', 'name': ' Redmi 8 印度版'}, {'model': 'M1908C3KE', 'name': ' Redmi 8A 全网通版'},
          {'model': 'M1908C3KG M1908C3KH', 'name': ' Redmi 8A 国际版'},
          {'model': 'M1908C3KI', 'name': ' Redmi 8A 印度版'},
          {'model': 'M2001C3K3I', 'name': ' Redmi 8A Dual 印度版 / Redmi 8A Pro 国际版'},
          {'model': 'M2004J19C', 'name': ' Redmi 9 全网通版'}, {'model': 'M2004J19G', 'name': ' Redmi 9 国际版'},
          {'model': 'M2004J19I', 'name': ' Redmi 9 Prime 印度版'},
          {'model': 'M2004J19AG', 'name': ' Redmi 9 国际版 (NFC)'},
          {'model': 'M2006C3LC', 'name': ' Redmi 9A 全网通版'}, {'model': 'M2006C3LG', 'name': ' Redmi 9A 国际版'},
          {'model': 'M2006C3LVG', 'name': ' Redmi 9AT 国际版'},
          {'model': 'M2006C3LI', 'name': ' Redmi 9A 印度版 / Redmi 9A Sport 印度版'},
          {'model': 'M2006C3LII', 'name': ' Redmi 9i 印度版 / Redmi 9i Sport 印度版'},
          {'model': 'M2006C3MG', 'name': ' Redmi 9C 国际版'}, {'model': 'M2006C3MT', 'name': ' Redmi 9C 泰国版'},
          {'model': 'M2006C3MNG', 'name': ' Redmi 9C NFC 国际版'},
          {'model': 'M2006C3MII', 'name': ' Redmi 9 印度版 / Redmi 9 Activ 印度版'},
          {'model': 'M2010J19SG', 'name': ' Redmi 9T 国际版'}, {'model': 'M2010J19SI', 'name': ' Redmi 9 Power 印度版'},
          {'model': 'M2010J19SR', 'name': ' Redmi 9T 日本版'}, {'model': 'M2010J19ST', 'name': ' Redmi 9T 泰国版'},
          {'model': 'M2010J19SY', 'name': ' Redmi 9T 国际版 (NFC)'},
          {'model': 'M2010J19SL', 'name': ' Redmi 9T 拉美版'}, {'model': '21061119AG', 'name': ' Redmi 10 国际版'},
          {'model': '21061119AL', 'name': ' Redmi 10 拉美版'},
          {'model': '21061119BI', 'name': ' Redmi 10 Prime 印度版'},
          {'model': '21061119DG', 'name': ' Redmi 10 国际版 (NFC)'},
          {'model': '21121119SG', 'name': ' Redmi 10 2022 国际版'},
          {'model': '21121119VL', 'name': ' Redmi 10 2022 拉美版'},
          {'model': '22011119TI', 'name': ' Redmi 10 Prime 2022 印度版'},
          {'model': '22011119UY', 'name': ' Redmi 10 2022 国际版 (NFC)'},
          {'model': '22041219G', 'name': ' Redmi 10 5G 国际版'},
          {'model': '22041219I', 'name': ' Redmi 11 Prime 5G 印度版'},
          {'model': '22041219NY', 'name': ' Redmi 10 5G 国际版 (NFC)'},
          {'model': '220333QAG', 'name': ' Redmi 10C 国际版'},
          {'model': '220333QBI', 'name': ' Redmi 10 印度版 / Redmi 10 Power 印度版'},
          {'model': '220333QNY', 'name': ' Redmi 10C 国际版 (NFC)'}, {'model': '220333QL', 'name': ' Redmi 10C 拉美版'},
          {'model': '220233L2C', 'name': ' Redmi 10A 全网通版'}, {'model': '220233L2G', 'name': ' Redmi 10A 国际版'},
          {'model': '220233L2I', 'name': ' Redmi 10A 印度版 / Redmi 10A Sport 印度版'},
          {'model': '22071219AI', 'name': ' Redmi 11 Prime 印度版'},
          {'model': '23053RN02A', 'name': ' Redmi 12 国际版'}, {'model': '23053RN02I', 'name': ' Redmi 12 印度版'},
          {'model': '23053RN02L', 'name': ' Redmi 12 拉美版'},
          {'model': '23053RN02Y', 'name': ' Redmi 12 国际版 (NFC)'},
          {'model': '23077RABDC', 'name': ' Redmi 12 5G 全网通版'},
          {'model': '23076RN8DY', 'name': ' Redmi 12 5G 国际版 (NFC)'},
          {'model': '23076RN4BI', 'name': ' Redmi 12 5G 印度版'},
          {'model': '22120RN86C', 'name': ' Redmi 12C 全网通版'}, {'model': '22120RN86G', 'name': ' Redmi 12C 国际版'},
          {'model': '2212ARNC4L', 'name': ' Redmi 12C 拉美版'},
          {'model': '22126RN91Y', 'name': ' Redmi 12C 国际版 (NFC)'},
          {'model': '2014018', 'name': ' 红米 Note 联通 3G 标准版'},
          {'model': '2013121', 'name': ' 红米 Note 联通 3G 增强版'},
          {'model': '2014017', 'name': ' 红米 Note 移动 3G 标准版'},
          {'model': '2013122', 'name': ' 红米 Note 移动 3G 增强版'},
          {'model': '2014022', 'name': ' 红米 Note 移动 4G 增强版'},
          {'model': '2014021', 'name': ' 红米 Note 联通 4G 增强版'},
          {'model': '2014715', 'name': ' 红米 Note 4G 国际版'}, {'model': '2014712', 'name': ' 红米 Note 4G 印度版'},
          {'model': '2014915', 'name': ' 红米 Note 移动 4G 双卡版'},
          {'model': '2014912', 'name': ' 红米 Note 联通 4G 双卡版'},
          {'model': '2014916', 'name': ' 红米 Note 电信 4G 双卡版'},
          {'model': '2014911', 'name': ' 红米 Note 移动 4G 双卡合约版'},
          {'model': '2014910', 'name': ' 红米 Note 电信 4G 双卡合约版'},
          {'model': '2015052', 'name': ' 红米 Note 2 移动版'}, {'model': '2015051', 'name': ' 红米 Note 2 双网通版'},
          {'model': '2015712', 'name': ' 红米 Note 2 双网通高配版'},
          {'model': '2015055', 'name': ' 红米 Note 2 移动合约版'},
          {'model': '2015056', 'name': ' 红米 Note 2 移动合约高配版'},
          {'model': '2015617', 'name': ' 红米 Note 3 双网通版'},
          {'model': '2015611', 'name': ' 红米 Note 3 移动合约版'},
          {'model': '2015112 2015115', 'name': ' 红米 Note 3 全网通版'},
          {'model': '2015116', 'name': ' 红米 Note 3 国际版'}, {'model': '2015161', 'name': ' 红米 Note 3 台湾特制版'},
          {'model': '2016050', 'name': ' 红米 Note 4 全网通版'}, {'model': '2016051', 'name': ' 红米 Note 4 移动版'},
          {'model': '2016101', 'name': ' 红米 Note 4X 高通 全网通版'},
          {'model': '2016130', 'name': ' 红米 Note 4X 高通 移动 4G+ 版'},
          {'model': '2016100 2016102', 'name': ' 红米 Note 4 国际版 / 红米 Note 4X 高通 国际版'},
          {'model': 'MBE6A5', 'name': ' 红米 Note 4X MTK 全网通版'},
          {'model': 'MBT6A5', 'name': ' 红米 Note 4X MTK 移动 4G+ 版'},
          {'model': 'MEI7', 'name': ' 红米 Note 5 印度版'}, {'model': 'MEE7S', 'name': ' 红米 Note 5 全网通版'},
          {'model': 'MET7S', 'name': ' 红米 Note 5 移动 4G+ 版'},
          {'model': 'MEC7S', 'name': ' 红米 Note 5 联通电信定制版'},
          {'model': 'M1803E7SG M1803E7SH', 'name': ' 红米 Note 5 国际版'},
          {'model': 'MEI7S', 'name': ' 红米 Note 5 Pro 印度版'},
          {'model': 'MDE6', 'name': ' 红米 Note 5A 全网通 标准版'},
          {'model': 'MDT6', 'name': ' 红米 Note 5A 移动 4G+ 标准版'},
          {'model': 'MDG6', 'name': ' 红米 Note 5A 国际版 标准版'}, {'model': 'MDI6', 'name': ' 红米 Y1 Lite 印度版'},
          {'model': 'MDE6S', 'name': ' 红米 Note 5A 全网通 高配版'},
          {'model': 'MDT6S', 'name': ' 红米 Note 5A 移动 4G+ 高配版'},
          {'model': 'MDG6S', 'name': ' 红米 Note 5A 国际版 高配版'}, {'model': 'MDI6S', 'name': ' 红米 Y1 印度版'},
          {'model': 'M1806E7TG M1806E7TH', 'name': ' 红米 Note 6 Pro 国际版'},
          {'model': 'M1806E7TI', 'name': ' 红米 Note 6 Pro 印度版'},
          {'model': 'M1901F7E', 'name': ' Redmi Note 7 全网通版'},
          {'model': 'M1901F7T', 'name': ' Redmi Note 7 移动 4G+ 版'},
          {'model': 'M1901F7C', 'name': ' Redmi Note 7 联通电信定制版'},
          {'model': 'M1901F7G M1901F7H', 'name': ' Redmi Note 7 国际版'},
          {'model': 'M1901F7I', 'name': ' Redmi Note 7 印度版 / Redmi Note 7S 印度版'},
          {'model': 'M1901F7BE', 'name': ' Redmi Note 7 Pro 全网通版'},
          {'model': 'M1901F7S', 'name': ' Redmi Note 7 Pro 印度版'},
          {'model': 'M1908C3JE', 'name': ' Redmi Note 8 全网通版'},
          {'model': 'M1908C3JC', 'name': ' Redmi Note 8 运营商全网通版'},
          {'model': 'M1908C3JG M1908C3JH', 'name': ' Redmi Note 8 国际版'},
          {'model': 'M1908C3JI', 'name': ' Redmi Note 8 印度版'},
          {'model': 'M1908C3XG', 'name': ' Redmi Note 8T 国际版'},
          {'model': 'M1908C3JGG', 'name': ' Redmi Note 8 (2021) 国际版'},
          {'model': 'M1906G7E', 'name': ' Redmi Note 8 Pro 全网通版'},
          {'model': 'M1906G7T', 'name': ' Redmi Note 8 Pro 运营商全网通版'},
          {'model': 'M1906G7G', 'name': ' Redmi Note 8 Pro 国际版'},
          {'model': 'M1906G7I', 'name': ' Redmi Note 8 Pro 印度版'},
          {'model': 'M2010J19SC', 'name': ' Redmi Note 9 4G 全网通版'},
          {'model': 'M2007J22C', 'name': ' Redmi Note 9 5G 全网通版'},
          {'model': 'M2003J15SS', 'name': ' Redmi Note 9 国际版'},
          {'model': 'M2003J15SI', 'name': ' Redmi Note 9 印度版'},
          {'model': 'M2003J15SG', 'name': ' Redmi Note 9 国际版 (NFC)'},
          {'model': 'M2007J22G', 'name': ' Redmi Note 9T 5G 国际版'},
          {'model': 'M2007J22R A001XM', 'name': ' Redmi Note 9T 5G 日本版 (SoftBank)'},
          {'model': 'M2007J17C', 'name': ' Redmi Note 9 Pro 5G 全网通版'},
          {'model': 'M2003J6A1G', 'name': ' Redmi Note 9S 国际版'},
          {'model': 'M2003J6A1R', 'name': ' Redmi Note 9S 日本版 / Redmi Note 9S 韩国版'},
          {'model': 'M2003J6A1I', 'name': ' Redmi Note 9 Pro 印度版'},
          {'model': 'M2003J6B1I', 'name': ' Redmi Note 9 Pro Max 印度版'},
          {'model': 'M2003J6B2G', 'name': ' Redmi Note 9 Pro 国际版'},
          {'model': 'M2101K7AG', 'name': ' Redmi Note 10 国际版'},
          {'model': 'M2101K7AI', 'name': ' Redmi Note 10 印度版'},
          {'model': 'M2101K7BG', 'name': ' Redmi Note 10S 国际版'},
          {'model': 'M2101K7BI', 'name': ' Redmi Note 10S 印度版'},
          {'model': 'M2101K7BNY', 'name': ' Redmi Note 10S 国际版 (NFC)'},
          {'model': 'M2101K7BL', 'name': ' Redmi Note 10S 拉美版'},
          {'model': 'M2103K19C', 'name': ' Redmi Note 10 5G 全网通版 / Redmi Note 11SE 全网通版'},
          {'model': 'M2103K19I', 'name': ' Redmi Note 10T 5G 印度版'},
          {'model': 'M2103K19G', 'name': ' Redmi Note 10 5G 国际版'},
          {'model': 'M2103K19Y', 'name': ' Redmi Note 10T 国际版'},
          {'model': 'M2104K19J XIG02', 'name': ' Redmi Note 10 JE 日本版 (KDDI)'},
          {'model': '22021119KR', 'name': ' Redmi Note 10T 日本版 (SIM Free)'},
          {'model': 'A101XM', 'name': ' Redmi Note 10T 日本版 (SoftBank)'},
          {'model': 'M2101K6G', 'name': ' Redmi Note 10 Pro 国际版'},
          {'model': 'M2101K6T', 'name': ' Redmi Note 10 Pro 泰国版'},
          {'model': 'M2101K6R', 'name': ' Redmi Note 10 Pro 日本版'},
          {'model': 'M2101K6P', 'name': ' Redmi Note 10 Pro 印度版'},
          {'model': 'M2101K6I', 'name': ' Redmi Note 10 Pro Max 印度版'},
          {'model': 'M2104K10AC', 'name': ' Redmi Note 10 Pro 5G 全网通版'},
          {'model': '2109106A1I', 'name': ' Redmi Note 10 Lite 印度版'},
          {'model': '21121119SC', 'name': ' Redmi Note 11 4G 全网通版'},
          {'model': '2201117TG', 'name': ' Redmi Note 11 国际版'},
          {'model': '2201117TI', 'name': ' Redmi Note 11 印度版'},
          {'model': '2201117TL', 'name': ' Redmi Note 11 拉美版'},
          {'model': '2201117TY', 'name': ' Redmi Note 11 国际版 (NFC)'},
          {'model': '21091116AC', 'name': ' Redmi Note 11 5G 全网通版'},
          {'model': '21091116AI', 'name': ' Redmi Note 11T 5G 印度版'},
          {'model': '22041219C', 'name': ' Redmi Note 11E 5G 全网通版'},
          {'model': '2201117SG', 'name': ' Redmi Note 11S 国际版'},
          {'model': '2201117SI', 'name': ' Redmi Note 11S 印度版'},
          {'model': '2201117SL', 'name': ' Redmi Note 11S 拉美版'},
          {'model': '2201117SY', 'name': ' Redmi Note 11S 国际版 (NFC)'},
          {'model': '22087RA4DI', 'name': ' Redmi Note 11 SE 印度版'},
          {'model': '22031116BG', 'name': ' Redmi Note 11S 5G 国际版'},
          {'model': '21091116C', 'name': ' Redmi Note 11 Pro 全网通版'},
          {'model': '2201116TG', 'name': ' Redmi Note 11 Pro 国际版'},
          {'model': '2201116TI', 'name': ' Redmi Note 11 Pro 印度版'},
          {'model': '2201116SC', 'name': ' Redmi Note 11E Pro 全网通版'},
          {'model': '2201116SG', 'name': ' Redmi Note 11 Pro 5G 国际版'},
          {'model': '2201116SR', 'name': ' Redmi Note 11 Pro 5G 日本版'},
          {'model': '2201116SI', 'name': ' Redmi Note 11 Pro+ 5G 印度版'},
          {'model': '21091116UC', 'name': ' Redmi Note 11 Pro+ 全网通版'},
          {'model': '21091116UG', 'name': ' Redmi Note 11 Pro+ 5G 国际版'},
          {'model': '22041216C', 'name': ' Redmi Note 11T Pro 全网通版'},
          {'model': '22041216UC', 'name': ' Redmi Note 11T Pro+ 全网通版'},
          {'model': '22095RA98C', 'name': ' Redmi Note 11R 5G 全网通版'},
          {'model': '23021RAAEG', 'name': ' Redmi Note 12 国际版'},
          {'model': '23027RAD4I', 'name': ' Redmi Note 12 印度版'},
          {'model': '23028RA60L', 'name': ' Redmi Note 12 拉美版'},
          {'model': '23021RAA2Y', 'name': ' Redmi Note 12 国际版 (NFC)'},
          {'model': '22101317C', 'name': ' Redmi Note 12 5G 全网通版 / Redmi Note 12R Pro 全网通版'},
          {'model': '22111317G', 'name': ' Redmi Note 12 5G 国际版'},
          {'model': '22111317I', 'name': ' Redmi Note 12 5G 印度版'},
          {'model': '23076RA4BC', 'name': ' Redmi Note 12R 全网通版'},
          {'model': '2303CRA44A', 'name': ' Redmi Note 12S 国际版'},
          {'model': '2303ERA42L', 'name': ' Redmi Note 12S 拉美版'},
          {'model': '23030RAC7Y', 'name': ' Redmi Note 12S 国际版 (NFC)'},
          {'model': '2209116AG', 'name': ' Redmi Note 12 Pro 国际版'},
          {'model': '22101316C', 'name': ' Redmi Note 12 Pro 全网通版'},
          {'model': '22101316G', 'name': ' Redmi Note 12 Pro 5G 国际版'},
          {'model': '22101316I', 'name': ' Redmi Note 12 Pro 5G 印度版'},
          {'model': '22101316UCP', 'name': ' Redmi Note 12 Pro+ 全网通版'},
          {'model': '22101316UG', 'name': ' Redmi Note 12 Pro+ 5G 国际版'},
          {'model': '22101316UP', 'name': ' Redmi Note 12 Pro+ 5G 印度版'},
          {'model': '22101316UC', 'name': ' Redmi Note 12 探索版 全网通版'},
          {'model': '22101320C', 'name': ' Redmi Note 12 Pro 极速版 全网通版'},
          {'model': '23054RA19C', 'name': ' Redmi Note 12T Pro 全网通版'},
          {'model': '23049RAD8C', 'name': ' Redmi Note 12 Turbo 全网通版'},
          {'model': 'M2004J7AC', 'name': ' Redmi 10X 5G 全网通版'},
          {'model': 'M2004J7BC', 'name': ' Redmi 10X Pro 5G 全网通版'},
          {'model': 'M2003J15SC', 'name': ' Redmi 10X 4G 全网通版'},
          {'model': 'M1903F10A', 'name': ' Redmi K20 全网通版'},
          {'model': 'M1903F10C', 'name': ' Redmi K20 运营商全网通版'},
          {'model': 'M1903F10I', 'name': ' Redmi K20 印度版'},
          {'model': 'M1903F11A', 'name': ' Redmi K20 Pro 全网通版'},
          {'model': 'M1903F11C', 'name': ' Redmi K20 Pro 运营商全网通版'},
          {'model': 'M1903F11I', 'name': ' Redmi K20 Pro 印度版'},
          {'model': 'M1903F11A', 'name': ' Redmi K20 Pro 尊享版 全网通版'},
          {'model': 'M2001G7AE', 'name': ' Redmi K30 5G 全网通版 / Redmi K30 5G 极速版'},
          {'model': 'M2001G7AC', 'name': ' Redmi K30 5G 全网通版'},
          {'model': 'M2001G7AC', 'name': ' Redmi K30i 5G 全网通版'},
          {'model': 'M1912G7BE', 'name': ' Redmi K30 4G 全网通版'},
          {'model': 'M1912G7BC', 'name': ' Redmi K30 4G 运营商全网通版'},
          {'model': 'M2001J11C', 'name': ' Redmi K30 Pro 全网通版'},
          {'model': 'M2001J11C M2001J11E', 'name': ' Redmi K30 Pro 变焦版 全网通版'},
          {'model': 'M2006J10C', 'name': ' Redmi K30 至尊纪念版 全网通版'},
          {'model': 'M2007J3SC', 'name': ' Redmi K30S 至尊纪念版 全网通版'},
          {'model': 'M2012K11AC', 'name': ' Redmi K40 全网通版'},
          {'model': 'M2012K11C', 'name': ' Redmi K40 Pro 全网通版 / Redmi K40 Pro+ 全网通版'},
          {'model': 'M2012K10C', 'name': ' Redmi K40 游戏增强版 全网通版'},
          {'model': '22021211RC', 'name': ' Redmi K40S 全网通版'},
          {'model': '22041211AC', 'name': ' Redmi K50 全网通版'},
          {'model': '22011211C', 'name': ' Redmi K50 Pro 全网通版'},
          {'model': '21121210C', 'name': ' Redmi K50 电竞版 全网通版'},
          {'model': '22081212C', 'name': ' Redmi K50 至尊版 全网通版'},
          {'model': '22041216I', 'name': ' Redmi K50i 印度版'}, {'model': '23013RK75C', 'name': ' Redmi K60 全网通版'},
          {'model': '22127RK46C', 'name': ' Redmi K60 Pro 全网通版'},
          {'model': '22122RK93C', 'name': ' Redmi K60E 全网通版'},
          {'model': '23078RKD5C', 'name': ' Redmi K60 至尊版 全网通版'},
          {'model': '2016020', 'name': ' 红米 Pro 标准版'}, {'model': '2016021', 'name': ' 红米 Pro 高配版 / 尊享版'},
          {'model': 'M1803E6E', 'name': ' 红米 S2 全网通版'}, {'model': 'M1803E6T', 'name': ' 红米 S2 移动 4G+ 版'},
          {'model': 'M1803E6C', 'name': ' 红米 S2 联通电信定制版'},
          {'model': 'M1803E6G M1803E6H', 'name': ' 红米 S2 国际版'}, {'model': 'M1803E6I', 'name': ' 红米 Y2 印度版'},
          {'model': 'M1810F6G', 'name': ' Redmi Y3 国际版'}, {'model': 'M1810F6I', 'name': ' Redmi Y3 印度版'},
          {'model': 'M1903C3GG M1903C3GH', 'name': ' Redmi Go 国际版'},
          {'model': 'M1903C3GI', 'name': ' Redmi Go 印度版'}, {'model': '220733SG', 'name': ' Redmi A1 国际版'},
          {'model': '220733SH 220733SI', 'name': ' Redmi A1 印度版'}, {'model': '220733SL', 'name': ' Redmi A1 拉美版'},
          {'model': '220733SFG', 'name': ' Redmi A1+ 国际版'},
          {'model': '220733SFH 220743FI', 'name': ' Redmi A1+ 印度版'},
          {'model': '23028RNCAG', 'name': ' Redmi A2+ 国际版'}, {'model': '22081283C', 'name': ' Redmi Pad 国行版'},
          {'model': '22081283G', 'name': ' Redmi Pad 国际版'}, {'model': '23073RPBFC', 'name': ' Redmi Pad SE 国行版'},
          {'model': '23073RPBFG', 'name': ' Redmi Pad SE 国际版'},
          {'model': '23073RPBFL', 'name': ' Redmi Pad SE 拉美版'}, {'model': 'M1805E10A', 'name': ' POCO F1'},
          {'model': 'M2004J11G', 'name': ' POCO F2 Pro 国际版'}, {'model': 'M2012K11AG', 'name': ' POCO F3 国际版'},
          {'model': 'M2104K10I', 'name': ' POCO F3 GT 印度版'}, {'model': '22021211RG', 'name': ' POCO F4 国际版'},
          {'model': '22021211RI', 'name': ' POCO F4 印度版'}, {'model': '21121210G', 'name': ' POCO F4 GT 国际版'},
          {'model': '21121210I', 'name': ' POCO F4 GT 印度版'}, {'model': '23049PCD8G', 'name': ' POCO F5 国际版'},
          {'model': '23049PCD8I', 'name': ' POCO F5 印度版'}, {'model': '23013PC75G', 'name': ' POCO F5 Pro 国际版'},
          {'model': 'M1912G7BI', 'name': ' POCO X2 印度版'}, {'model': 'M2007J20CI', 'name': ' POCO X3 印度版'},
          {'model': 'M2007J20CG', 'name': ' POCO X3 NFC 国际版'},
          {'model': 'M2007J20CT', 'name': ' POCO X3 NFC 泰国版'},
          {'model': 'M2102J20SG', 'name': ' POCO X3 Pro 国际版'},
          {'model': 'M2102J20SI', 'name': ' POCO X3 Pro 印度版'}, {'model': '21061110AG', 'name': ' POCO X3 GT 国际版'},
          {'model': '2201116PG', 'name': ' POCO X4 Pro 5G 国际版'},
          {'model': '2201116PI', 'name': ' POCO X4 Pro 5G 印度版'},
          {'model': '22041216G', 'name': ' POCO X4 GT 国际版'},
          {'model': '22041216UG', 'name': ' POCO X4 GT Pro 国际版'},
          {'model': '22111317PG', 'name': ' POCO X5 5G 国际版'}, {'model': '22111317PI', 'name': ' POCO X5 5G 印度版'},
          {'model': '22101320G', 'name': ' POCO X5 Pro 5G 国际版'},
          {'model': '22101320I', 'name': ' POCO X5 Pro 5G 印度版'}, {'model': 'M2004J19PI', 'name': ' POCO M2 印度版'},
          {'model': 'M2003J6CI', 'name': ' POCO M2 Pro 印度版'}, {'model': 'M2010J19CG', 'name': ' POCO M3 国际版'},
          {'model': 'M2010J19CT', 'name': ' POCO M3 泰国版'}, {'model': 'M2010J19CI', 'name': ' POCO M3 印度版'},
          {'model': 'M2103K19PI', 'name': ' POCO M3 Pro 5G 印度版'},
          {'model': '22041219PG', 'name': ' POCO M4 5G 国际版'}, {'model': '22041219PI', 'name': ' POCO M4 5G 印度版'},
          {'model': '2201117PG', 'name': ' POCO M4 Pro 国际版'}, {'model': '2201117PI', 'name': ' POCO M4 Pro 印度版'},
          {'model': '21091116AG', 'name': ' POCO M4 Pro 5G 国际版'},
          {'model': '22031116AI', 'name': ' POCO M4 Pro 5G 印度版'}, {'model': '22071219CG', 'name': ' POCO M5 国际版'},
          {'model': '22071219CI', 'name': ' POCO M5 印度版'}, {'model': '2207117BPG', 'name': ' POCO M5s 国际版'},
          {'model': '23076PC4BI', 'name': ' POCO M6 Pro 5G 印度版'}, {'model': 'M2006C3MI', 'name': ' POCO C3 印度版'},
          {'model': '211033MI', 'name': ' POCO C31 印度版'}, {'model': '220333QPG', 'name': ' POCO C40 国际版'},
          {'model': '220333QPI', 'name': ' POCO C40 印度版'},
          {'model': '220733SPH 220733SPI', 'name': ' POCO C50 印度版'},
          {'model': '2305EPCC4G', 'name': ' POCO C51 国际版'}, {'model': '22127PC95G', 'name': ' POCO C55 国际版'},
          {'model': 'XMWT01', 'name': ' 小米手表'}, {'model': 'FYJ01QP', 'name': ' 小米米家翻译机'},
          {'model': '21051191C', 'name': ' CyberDog 仿生四足机器人'}]

def random_version():
    version_list = [
        {
            "v": "1.38.0",
            "algorithms": [{"alg": "md5", "salt": "Z1GUH9FPdd2uR48"},
                           {"alg": "md5", "salt": "W4At8CN00YeICfrhKye"},
                           {"alg": "md5", "salt": "WbsJsexMTIj+qjuVNkTZUJxqUkdf"},
                           {"alg": "md5", "salt": "O56bcWMoHaTXey5QnzKXDUETeaVSD"},
                           {"alg": "md5", "salt": "nAN3jBriy8/PXGAdsn3yPMU"},
                           {"alg": "md5", "salt": "+OQEioNECNf9UdRe"},
                           {"alg": "md5", "salt": "2BTBxZ3IbPnkrrfd/"},
                           {"alg": "md5", "salt": "gBip5AYtm53"},
                           {"alg": "md5", "salt": "9FMyrvjZFZJT5Y+b1NeSYfs5"},
                           {"alg": "md5", "salt": "0cIBtEVWYCKdIOlOXnTJPhLGU/y5"},
                           {"alg": "md5", "salt": "92j4I+ZiMyxFx6Q"},
                           {"alg": "md5", "salt": "xNFN9RnUlu218s"},
                           {"alg": "md5", "salt": "UZcnnQ2nkaY0S"}]
        },
        {
            "v": "1.39.0",
            "algorithms": [{"alg": "md5", "salt": "e1d0IwHdz+CJLzskoFto8SSKobPWMwcz"},
                           {"alg": "md5", "salt": "wUU7Rz/wpuHy"},
                           {"alg": "md5", "salt": "dye78dKP7wgEFMebN/Z11VVPAAtueAVR3TcMFZPCO0F9mBQqbk/qpHy9Yqr0no"},
                           {"alg": "md5", "salt": "Cpx1E/O+bo+vTguIiLosm3zR9Y1N"},
                           {"alg": "md5", "salt": "uqyFMWT5R6TxXji2DhHxlNYY3"},
                           {"alg": "md5", "salt": "7afNTr/GwzoNJCLXJVm+nEMBa2w8PiwBfm"},
                           {"alg": "md5", "salt": "glbIrXW34T5ceIBUhsAOzT1R0XSHnTwv1mqtg1r"},
                           {"alg": "md5", "salt": "l"},
                           {"alg": "md5", "salt": "51sgGDapT73pQMI664"}]

        },
        {
            "v": "1.40.0",
            "algorithms": [{"alg": "md5", "salt": "MNn/o2kDbAdap6iyA62c31+odfAXm"},
                           {"alg": "md5", "salt": "GU2DNPxJQz8Zd/HZhKe+Vpr3nydASi"},
                           {"alg": "md5", "salt": "Mr"},
                           {"alg": "md5", "salt": "9yuMfCUj3370cqowx0iLT4WI"},
                           {"alg": "md5", "salt": "sEtFM"},
                           {"alg": "md5", "salt": "57O4iXpaXLGJ5CuIXlKWm"},
                           {"alg": "md5", "salt": "jIPlqvJR/1fNI3v4IvFcRv2IlzSuUc"},
                           {"alg": "md5", "salt": "p0u2aV"},
                           {"alg": "md5", "salt": "AnHbAEWs+4ggDbg37bbpULXK2NFyFHSE"},
                           {"alg": "md5", "salt": "X3v/UHqblw2VHjeCJHamvXyB"},
                           {"alg": "md5", "salt": "Lxe9yYKLa7JBTw3AKivrzs+CqdGO39K"},
                           {"alg": "md5", "salt": "lkz8Q4viV1+U"},
                           {"alg": "md5", "salt": "VH2I"}]

        },
        {
            "v": "1.41.0",
            "algorithms": [{"alg": "md5", "salt": "Wcpe+bWhLidcpKx+NbicS9tmSq8RbVTFk6Arf"},
                           {"alg": "md5", "salt": "/WcDjchZab"},
                           {"alg": "md5", "salt": "YWRJGUPI/lD"},
                           {"alg": "md5", "salt": "R"},
                           {"alg": "md5", "salt": "9Kba0Nkh7vz5CGWxgFCyqJ/BdjnJIx8KU5r/WTR6Ae"},
                           {"alg": "md5", "salt": "tmUQGnovPWmNvB0UAQbDZnJMg57jGzUv7"},
                           {"alg": "md5", "salt": "sPsOQdEqCp19PUDMYfg1//"},
                           {"alg": "md5", "salt": "mvhuvTJROSortMaGzK5rZi209sBTZq+WitI"},
                           {"alg": "md5", "salt": "Qox5BNaQfdishhmAKGr"},
                           {"alg": "md5", "salt": "R2JW9N8bRUEizf+pkWg/o9iJKG34bdpSjEe"},
                           {"alg": "md5", "salt": "FvDT"}]

        },
        {
            "v": "1.42.6",
            "algorithms": [{"alg": "md5", "salt": "frupTFdxwcJ5mcL3R8"},
                           {"alg": "md5", "salt": "jB496fSFfbWLhWyqV"},
                           {"alg": "md5", "salt": "xYLtzn8LT5h3KbAalCjc/Wf"},
                           {"alg": "md5", "salt": "PSHSbm1SlxbvkwNk4mZrJhBZ1vsHCtEdm3tsRiy1IPUnqi1FNB5a2F"},
                           {"alg": "md5", "salt": "SX/WvPCRzgkLIp99gDnLaCs0jGn2+urx7vz/"},
                           {"alg": "md5", "salt": "OGdm+dgLk5EpK4O1nDB+Z4l"},
                           {"alg": "md5", "salt": "nwtOQpz2xFLIE3EmrDwMKe/Vlw2ubhRcnS2R23bwx9wMh+C3Sg"},
                           {"alg": "md5", "salt": "FI/9X9jbnTLa61RHprndT0GkVs18Chd"}]

        }
    ]
    return random.choice(version_list)
# 随机密码
def getRandom(randomlength=10):
    """
  生成一个指定长度的随机字符串
  """
    digits = '0123456789'
    ascii_letters = 'abcdefghigklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    str_list = [random.choice(digits + ascii_letters) for i in range(randomlength)]
    random_str = ''.join(str_list)
    return random_str

# md5加密算法
def get_hash(str):
    obj = hashlib.md5()
    obj.update(str.encode("utf-8"))
    result = obj.hexdigest()
    return result
def get_ua_key(device_id):
    rank_1 = hashlib.sha1((device_id + "com.pikcloud.pikpak1appkey").encode("utf-8")).hexdigest()
    rank_2 = get_hash(rank_1)
    return device_id + rank_2
# 获取UA
def get_User_Agent(client_id, device_id, ua_key, timestamp, phoneModel, phoneBuilder, version):
    UA = "ANDROID-com.pikcloud.pikpak/" + version + " protocolversion/200 accesstype/ clientid/" + client_id + " clientversion/" + version + " action_type/ networktype/WIFI sessionid/ deviceid/" + device_id + " providername/NONE devicesign/div101." + ua_key + " refresh_token/ sdkversion/1.1.0.110000 datetime/" + timestamp + " usrno/ appname/android-com.pikcloud.pikpak session_origin/ grant_type/ appid/ clientip/ devicename/" + phoneBuilder.capitalize() + "_" + phoneModel.capitalize() + " osversion/13 platformversion/10 accessmode/ devicemodel/" + phoneModel
    return UA
# 获取ua
def get_user_agent():
    tmp1 = random.randrange(90, 120)
    tmp2 = random.randrange(5200, 5500)
    tmp3 = random.randrange(90, 180)
    tmp_version = str(tmp1) + ".0." + str(tmp2) + "." + str(tmp3)
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/' + tmp_version + ' Safari/537.36 '
    print(ua)
    return ua
# -------------------------- 主函数一系列网络请求--------------------------
invite_success_limit = 1
invitation_records = {}

def main(invite_code, card_key, num_invitations=5):
    now = datetime.datetime.now()
    print("当前日期: ", now)
    start_time = time.time()
    success_count = 0
    global invitation_records
    current_time = time.time()

    if invite_code in invitation_records:
        last_submissions = invitation_records[invite_code]
        last_submissions = [
            t for t in last_submissions if current_time - t < 36000] # 10小时
        if len(last_submissions) >= 1:
            return "24小时内已提交1次，请明日再试。"
        invitation_records[invite_code] = last_submissions
    else:
        invitation_records[invite_code] = []

    while success_count < num_invitations:
        try:
            version_item = random_version()
            client_id = "YNxT9w7GMdWvEOKa"
            device_id = str(uuid.uuid4()).replace("-", "")
            timestamp = str(int(time.time()) * 1000)

            email_users, email_passes = read_and_process_file(file_path)

            if not email_users or not email_passes:
                return "暂无可用邮箱"
            email = email_users[0]
            email_password = email_passes[0]

            for email_user, email_pass in zip(email_users, email_passes):
                mail = email_user

                org_str = client_id + version_item['v'] + "com.pikcloud.pikpak" + device_id + timestamp
                captcha_sign = get_sign(org_str, version_item['algorithms'])

                randomPhone = random.choice(uaList)
                print(randomPhone)
                phoneModel = randomPhone['model']
                phoneBuilder = "XIAOMI"
                ua_key = get_ua_key(device_id)
                User_Agent = get_User_Agent(client_id, device_id, ua_key, timestamp, phoneModel, phoneBuilder, version_item['v'])
                user_agent = get_user_agent()

                # 1、初步安全验证
                meta0 = {
                    "email": email
                }
                # 执行初始化安全验证
                Init = init(client_id, "", device_id, user_agent,
                                "POST:/v1/auth/verification", meta0)
                if (Init == '连接超时'):
                     print('未检测')
                     return "连接超时,请刷新重试，多次失败请联系管理员查看代理池"
                captcha_token_info = Init["captcha_token"]
                Verification = verification(client_id, captcha_token_info, email, device_id, user_agent)

                # 获取验证码
                code = get_email_with_third_party(mail, email_user, email_pass)

                if not code:
                    print(f"无法从邮箱获取验证码: {mail}")
                    # 获取当前时间
                    current_timestamp = time.time()
                    update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
                    return "邮箱登录/验证失败，请刷新重试"

                # 使用验证码完成其他操作
                verification_response = verify(client_id, Verification['verification_id'], code, device_id, User_Agent)
                if(verification_response == '验证码不正确'):
                    # 获取当前时间
                    current_timestamp = time.time()
                    update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
                    return '验证码不正确'
                timestamp = str(int(time.time()) * 1000)
                org_str = client_id + version_item['v'] + "com.pikcloud.pikpak" + device_id + timestamp
                captcha_sign = get_sign(org_str, version_item['algorithms'])
                current_time = str(int(time.time()))
                # 二次安全验证
                meta1 = {
                    "captcha_sign": "1." + captcha_sign,
                    "user_id": "",
                    "package_name": "com.pikcloud.pikpak",
                    "client_version": version_item['v'],
                    "timestamp": timestamp
                }
                captcha_token = init1(client_id, captcha_token_info, device_id, User_Agent,
                             "POST:/v1/auth/signup", meta1)['captcha_token']
                
                client_secret = "dbw2OtmVEeuUvIptb1Coyg"
                name = email.split("@")[0]
                password = getRandom()
                
                # 账号注册 
                signup_response = signup(client_id, captcha_token, client_secret, email, name, password, verification_response['verification_token'],
                                        device_id, User_Agent)
                user_id = signup_response['sub']
                # 三次安全验证
                meta2 = {
                    "captcha_sign": "1." + captcha_sign,
                    "user_id": user_id,
                    "package_name": "com.pikcloud.pikpak",
                    "client_version": version_item['v'],
                    "timestamp": timestamp
                }
                captcha_token = init1(client_id, captcha_token, device_id, User_Agent,
                                    "POST:/vip/v1/activity/invite", meta2)["captcha_token"]
                # 8、邀请填写

                invite(user_id, phoneModel, phoneBuilder, invite_code, captcha_token, device_id,
                signup_response['access_token'], User_Agent, version_item['v'])
                activation_code(user_id, phoneModel, phoneBuilder, invite_code, captcha_token, device_id,
                    signup_response['access_token'], User_Agent)
                end_time = time.time()
                run_time = f'{(end_time - start_time):.2f}'

                # 检查邀请是否成功
                # 目前会员邀请之后会有最高24小时的审核，所以会一直显示失败
                # 如果会员天数等于5 邀请成功
                
                result = f'邀请成功(待定): {invite_code} 请重新打开邀请页面，查看邀请记录是否显示‘待定’'
                print(result)
                success_count += 1
                # 邀请时间限制
                invitation_records[invite_code].append(time.time())
                # 获取当前时间
                current_timestamp = time.time()
                # 更新文件中的邮箱和密码状态 添加时间
                update_file_status(r'./email.txt', email_user, password, "登录成功(待定)", current_timestamp)
                # 更新卡密使用次数
                card_keys[card_key] -= 1
                save_card_keys(card_keys)  # 保存更新后的卡密信息
                return f"邀请成功(待定): {invite_code} 运行时间: {run_time}秒<br> 邮箱: {mail} <br> 密码: {password} <br>请重新打开邀请页面，查看邀请记录是否显示‘待定’"

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
        # 请求Flask API获取启用的公告（后端需要支持启用公告的API）
        response = requests.get('http://127.0.0.1:5000/api/announcement/active')  # 假设有一个返回启用公告的API
        response.raise_for_status()  # 检查是否有HTTP错误
        data = response.json()  # 将返回的JSON数据转换为Python字典
        
        if data.get('error'):
            print("未找到启用的公告")
            return None

        is_enabled = data['enable']  # 获取是否开启公告
        announcement_title = data['title']
        announcement_message = data['message']

    except requests.exceptions.RequestException as e:
        # 如果API调用失败，打印错误信息并跳过公告处理
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
        input("请输入你的邀请码6-8位数字:", name="invite_code", type=TEXT,
              required=True, placeholder="打开pikpak我的界面-引荐奖励计划-获取邀请码数字"),
        input("请输入卡密:", name="card_key", type=TEXT,
              required=True, placeholder="请输入卡密")
    ])
    invite_code = form_data['invite_code']
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
        # futures = [executor.submit(main, invite_code) for _ in range(numberInvitations)]
        futures = [executor.submit(main, invite_code, card_key) for _ in range(1)]
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
    app.run(host='0.0.0.0', port=5000, debug=False)
