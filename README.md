


# 项目说明

## pikpak会员自动邀请辅助程序
## 原作者：B站纸鸢的花语
## 二改作者：非雨 
GitHub：[https://github.com/liuxianlu/pikpak_werbio](https://github.com/liuxianlu/pikpak_werbio)

### 注意
现在邀请新用户后，会有最高24小时的审核期，会员奖励不会立即结算  
![image](https://github.com/user-attachments/assets/29f795d0-bc14-48a7-884b-293c2701a613)

### 会员邀请主程序
![image](https://github.com/user-attachments/assets/cb68f956-921c-4f74-b844-32442184ae32)

### 代理池  
代理池项目:[ProxyPoolWithUI](https://github.com/OxOOo/ProxyPoolWithUI?tab=readme-ov-file)  
![image](https://github.com/user-attachments/assets/25e50193-59cf-4e39-8cb5-07d253c9730a)




### 登录页面
请在登录页部分，更改默认账号密码  
![image](https://github.com/user-attachments/assets/2f890414-ceea-44f4-b07e-88de4f3c9ef0)

### 邮箱管理页面
可以查看和管理已使用和未使用的邮箱  
![image](https://github.com/user-attachments/assets/6d37f883-857a-458b-95a0-e2b1da9f3558)
![image](https://github.com/user-attachments/assets/f3628ced-bb93-44b3-8987-4b6f6cebf9aa)

### 添加邮箱页面
可以手动添加邮箱信息，也可以从下方邮箱卡购买网站中购买邮箱卡，注意是邮箱卡，不要买成邮箱  
把你的key填入后进行更新，输入数量后获取账号，可以自动添加到右方文本框中  
![image](https://github.com/user-attachments/assets/9962762c-8974-48f0-a9d1-973e4234def0)


### 会员共享页面
只会显示近三天邀请成功的账号  
注意渲染时的密码是固定的，请确保与会员邀请程序中的密码一致
![image](https://github.com/user-attachments/assets/a3fc3c51-cc96-4917-9a9c-ddcec9478553)

### 卡密管理页面
支持增加、删除卡密，修改现有卡密  
![image](https://github.com/user-attachments/assets/795fafe7-820e-46d1-bbdd-5123bdac0a88)

### 是否公开
所有页面默认都是需要登陆后查看的，可以自行独立出部分页面  
以共享页面为例：  
只要删除选中的这两行即可  
![image](https://github.com/user-attachments/assets/253f1364-595c-4d00-8561-095da1587e0a)

### 邮箱接口
邮箱卡购买地址:
- [https://shanyouxiang.com/](https://shanyouxiang.com/)


## 运行
安装依赖 
```
pip install -r requirements.txt
```  
运行 gather.py
```
python gather.py
```
