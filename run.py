import os
import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
import poplib
import hashlib
import urllib.parse
import json
import random
import re
import logging
import time
import requests
import uuid
import email
import threading
# from datetime import datetime
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
# 创建一个自定义日志过滤器
class RequestFilter(logging.Filter):
    def filter(self, record):
        
        # 过滤掉包含 '/?app=index' 的日志
        if '/?app=index' in record.getMessage():
            return False
        # 过滤掉包含 'GET /get_status' 的日志
        if 'GET /get_status' in record.getMessage():
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
            'next_check': 0,
            'now_check': 0
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
                    fixed_password = "Bocchi002b"  # 固定密码 需要和下面邀请部分的密码一致
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
    print('尝试登录邮箱')
    
    while retries < max_retries:
        try:
            print('第', retries, '次尝试获取')  
            mail = poplib.POP3_SSL(pop3_server, 995)
            mail.user(email_user)
            mail.pass_(email_pass)
            print('获取邮箱列表')  
            # 获取邮件列表
            num_messages = len(mail.list()[1])
            for i in range(num_messages):
                response, lines, octets = mail.retr(i + 1)
                raw_email = b'\n'.join(lines)
                code = process_email(raw_email, i + 1, mail)
                
                # 如果处理函数返回了 code，立即返回
                if code:
                    return code
            
            mail.quit()
        except poplib.error_proto as e:
            print(f"POP3 错误: {e}")
        except Exception as e:
            print(f"发生错误: {type(e).__name__}: {e}")
        
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


def getuuid():
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


def md51(input_string):
    return hashlib.md5(input_string.encode()).hexdigest()

def get_sign1(xid, t):
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
        md5_hash = md51(md5_hash)
    
    # URL 编码
    encoded_hash = urllib.parse.quote(md5_hash)
    return encoded_hash
def get_proxy_ip(proxy):
    # 通过配置代理访问一个获取IP地址的服务
    url = 'http://httpbin.org/ip'
    
    try:
        response = requests.get(url, proxies=proxy)
        # 获取返回的IP地址
        ip_address = response.json()['origin']
        return ip_address
    except Exception as e:
        return f"Error: {e}"
    
# 初始安全验证
def init(xid, mail,proxy):
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
    retries = 1
    max_retries = 4
    while retries < max_retries:
        try:
            print('第',retries,'次尝试')
            response = requests.post(
                url, json=body, headers=headers,proxies=proxy, timeout=5)
            response_data = response.json()
            print('初始安全验证')
            # print(response_data)
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
    print('尝试发送验证码')
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers ,timeout=5)
            response_data = response.json()
            print('发送验证码')
            print(response_data)
            return response_data
        except:
            retries += 1
    return '连接超时'

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
    print('验证码验证')
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            # 遍历 details 列表，检查是否有包含 '验证码不正确' 的 message
            for detail in response_data.get('details', []):
                if 'message' in detail and '验证码不正确' in detail['message']:
                    return '验证码不正确'
            return response_data
        except:
            retries += 1
    return '连接超时'

# 验证注册结果
def signup(xid, mail, code, verification_token):
    global randint_ip
    url = 'https://user.mypikpak.com/v1/auth/signup'
    body = {
        "email": mail,
        "verification_code": code,
        "verification_token": verification_token,
        'name': f'qihang{random.randint(1, 1000000000)}vip',
        "password": "Bocchi002b",
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
    print('注册验证')
    while retries < max_retries:
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=5)
            response_data = response.json()
            print('验证注册结果')
            return response_data
        except:
            retries += 1
    return '连接超时'

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
    return '连接超时'

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
    return '连接超时'

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
    return '连接超时'

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
    return '连接超时'
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

def update_now_check(new_now_check):
    try:
        # 读取现有的 JSON 数据
        if os.path.getsize(STATUS_FILE) == 0:  # 检查文件是否为空
            raise ValueError("JSON file is empty")
        with open(STATUS_FILE, 'r') as f:
            data = json.load(f)
         # 获取现有的 'next_check' 和 'interval' 值
        next_check = data.get('next_check')
        
        
        if(new_now_check < next_check):
            data['now_check'] = new_now_check
        else:
            data['now_check'] = next_check
        # 写回到文件中
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f)
        
        
    except json.JSONDecodeError:
        raise ValueError("JSON file contains invalid data")
    except Exception as e:
        raise ValueError(f"Error updating 'now_check' in status file: {str(e)}")



@app.route('/get_status')
def get_status():
    try:
        update_now_check(time.time())  # 将 now_check 更新为当前时间戳
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
        # 记录当前检测的开始时间
        now_check_time = time.time()

        check_emails_multithread(read_email_file(file_path), file_path, max_workers)

        # 检测完成后，设置下一次检测的时间
        next_check_time = time.time() + interval

        write_status({
            'detection_active': detection_active,
            'interval': interval,
            'next_check': next_check_time,
            'now_check': now_check_time
        })

        # 设置事件，通知任务已完成
        detection_event.set()

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
        now_check_time = time.time()
        write_status({
            'detection_active': detection_active,
            'interval': interval,
            'next_check': next_check_time,
            'now_check': now_check_time
        })
        return jsonify({'status': 'started'})
    
    elif action == 'stop' and detection_active:
        detection_active = False
        detection_event.set()  # 触发事件，通知任务停止
        if detection_thread:
            detection_thread.join(timeout=10)  # 等待最多10秒
        # 更新状态文件
        write_status({
            'detection_active': detection_active,
            'interval': interval,
            'next_check': 0,  # 停止检测时，下次检查时间设为0
            'now_check': 0
        })
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'error'})

# -------------------------- 主函数一系列网络请求--------------------------
invite_success_limit = 1
invitation_records = {}

def main(incode, card_key):
    if card_key not in card_keys or card_keys[card_key] <= 0:
        return {'error': "卡密无效，联系客服"}
    now = datetime.datetime.now()
    print("当前日期: ", now)

    global invitation_records
    current_time = time.time()

    if incode in invitation_records:
        last_submissions = invitation_records[incode]
        last_submissions = [
            t for t in last_submissions if current_time - t < 36000] # 10小时
        if len(last_submissions) >= 1:
            return {'error': "24小时内已提交1次，请明日再试。"}
        invitation_records[incode] = last_submissions
    else:
        invitation_records[incode] = []

    print('生成xid')
    xid = getuuid()
    email_users, email_passes = read_and_process_file(file_path)

    if not email_users or not email_passes:
        return {'error': "暂无可用邮箱"}

    for email_user, email_pass in zip(email_users, email_passes):
        mail = email_user
        proxy = get_proxy()
        print('获取到的代理为:',proxy)
        # 执行初始化安全验证
        Init = init(xid, mail, proxy)
        
        if (Init == '连接超时'):
                return {'error': "连接超时,请刷新重试，多次失败请联系管理员查看代理池"}
        reCaptcha_url = Init['url'] + '&redirect_uri=https%3A%2F%2Fmypikpak.com%2Floading&state=getcaptcha' + str(round(time.time()*1000))

        # 保存 mail 和 xid 到会话
        session['mail'] = mail
        session['xid'] = xid
        session['email_user'] = email_user
        session['email_pass'] = email_pass
        session['proxy'] = proxy
        session['incode'] = incode
        session['card_key'] = card_key

        # 返回需要验证的链接给前端
        return {'captcha_url': reCaptcha_url}
def main2(captcha_token,incode,card_key,email_user,email_pass,proxy,xid,):
    start_time = time.time()
    success_count = 0
    mail = email_user

    Verification = verification(captcha_token, xid, mail)
    if 'error' in Verification.keys():
        return {'error':'安全验证失败，请确定复制的链接是跳转之后的链接<br>或者请尝试更换浏览器<br>电脑推荐使用edge游览器<br>手机推荐使用X浏览器'}
    # 获取验证码
    code = get_email_with_third_party(mail, email_user, email_pass)

    if not code:
        print(f"无法从邮箱获取验证码: {mail}")
        # 获取当前时间
        current_timestamp = time.time()
        update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
        return {'error': "邮箱登录/验证失败，请刷新重试"}

    # 使用验证码完成其他操作
    verification_response = verify(xid, Verification['verification_id'], code)
    if(verification_response == '验证码不正确'):
        # 获取当前时间
        current_timestamp = time.time()
        update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
        return {'error': "验证码不正确"}
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
        result = f"邀请成功 邀请码: {incode} email: {mail} 密码：Bocchi002b"
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
        return {
        'message': f"邀请成功: {incode} 运行时间: {run_time}秒",
        'email': mail,
        'password': 'Bocchi002b'
        }
    # 如果会员天数等于0 邀请成功(待定)
    elif activation.get('add_days') == 0:
        result = f'邀请成功(待定): {incode} 请重新打开邀请页面，查看邀请记录是否显示‘待定’'
        print(result)
        success_count += 1
        # 邀请时间限制
        # invitation_records[incode].append(time.time())
        # 获取当前时间
        current_timestamp = time.time()
        # 更新文件中的邮箱和密码状态 添加时间
        update_file_status(r'./email.txt', email_user, email_pass, "登录成功(待定)", current_timestamp)
        # 更新卡密使用次数
        card_keys[card_key] -= 1
        save_card_keys(card_keys)  # 保存更新后的卡密信息
        return {'message': f"邀请成功(待定): {incode} 运行时间: {run_time}秒<br>请重新打开邀请页面，查看邀请记录是否显示‘待定’<br>邮箱：{mail}<br>密码：Bocchi002b"}
    else:
        result = f"未知情况: {activation}"
        print(result)
        # 获取当前时间
        current_timestamp = time.time()
        update_file_status(r'./email.txt', email_user, email_pass, "失败", current_timestamp)
        return {'error': "未知情况"}

# html页面
@app.route('/')
def vip():
    is_enabled = False
    announcement_title = ""
    announcement_message = ""

    # 尝试调用API获取公告内容
    try:
        # 请求Flask API获取启用的公告（假设后端API是这个地址）
        response = requests.get('http://127.0.0.1:5000/api/announcement/active')
        response.raise_for_status()  # 检查是否有HTTP错误
        data = response.json()  # 将返回的JSON数据转换为Python字典

        if data.get('error'):
            print("未找到启用的公告")
        else:
            is_enabled = data['enable']  # 获取是否开启公告
            announcement_title = data['title']
            announcement_message = data['message']

    except requests.exceptions.RequestException as e:
        print(f"API调用失败: {e}")

    # 渲染网页模板，传递公告状态和内容
    return render_template(
        'vip.html',
        is_enabled=is_enabled,
        announcement_title=announcement_title,
        announcement_message=announcement_message
    )

@app.route('/submit', methods=['POST'])
def submit():
    incode = request.form.get('incode')
    card_key = request.form.get('card_key')

    session['incode'] = incode
    session['card_key'] = card_key

    return redirect(url_for('waiting'))



@app.route('/process', methods=['POST'])
def process():
    incode = session.get('incode')
    card_key = session.get('card_key')

    # 调用主逻辑，获取结果
    result = main(incode, card_key)

    # 检查是否有错误
    if 'error' in result:
        return jsonify({'redirect': url_for('error', error_message=result['error'])})

    if result.get('captcha_url'):
        return jsonify({'redirect': url_for('captcha', url=result['captcha_url'])})

    # 成功则返回结果页面的URL
    return jsonify({'redirect': url_for('error', error_message='未知错误')})

@app.route('/captcha')
def captcha():
    # 获取 reCaptcha 的 URL
    captcha_url = request.args.get('url')
    return render_template('captcha.html', captcha_url=captcha_url)

@app.route('/captcha_verify', methods=['POST'])
def captcha_verify():
    input_url = request.form.get('input_url')

    session['input_url'] = input_url

    # 渲染等待页面并告诉它是验证码验证的逻辑
    return render_template('waiting.html', captcha_verify=True)


@app.route('/process_captcha', methods=['POST'])
def process_captcha():
    # 获取session中的数据
    input_url = session.get('input_url')
    parsed_url = urlparse(input_url)
    query_params = parse_qs(parsed_url.query)
    captcha_token = query_params.get('captcha_token', [''])[0]

    xid = session.get('xid')
    email_user = session.get('email_user')
    email_pass = session.get('email_pass')
    proxy = session.get('proxy')
    incode = session.get('incode')
    card_key = session.get('card_key')

    # 继续主逻辑
    result = main2(captcha_token, incode, card_key, email_user, email_pass, proxy, xid)

    # 返回处理结果，重定向到相应页面
    if 'error' in result:
        return jsonify({'redirect': url_for('error', error_message=result['error'])})
    
    return jsonify({'redirect': url_for('result', result_message=result['message'])})



@app.route('/waiting')
def waiting():
    return render_template('waiting.html')

@app.route('/result')
def result():
    result_message = request.args.get('result_message')
    return render_template('result.html', result_message=result_message)

@app.route('/error')
def error():
    error_message = request.args.get('error_message')
    return render_template('error.html', error_message=error_message)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
