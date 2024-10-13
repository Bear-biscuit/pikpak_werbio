
# 项目说明

## pikpak会员自动邀请程序
感谢AAA大佬提供的[参数接口](https://doc.apipost.net/docs/detail/314e89ad4864000?target_id=34e75066b2f002)  

## 原作者：B站纸鸢的花语
倒卖 牡蛎😘~~~

## 自动获取验证码版本注意事项  
目前自动获取验证码版本已经复活  
感谢纸鸢大佬的[提取验证码](https://github.com/kiteyuan/Pikpak-Verification-Code)项目  
自动获取验证码需要提供以下信息  
```
email
password
refresh_token
client_id
```
示例  
```
闪邮箱提供的邮箱信息(此为举例参考):

[email] f73e6XXXlt1g@hotmail.com
[password] GDrQ2BSb8
[refresh_token] M.C523_BAY.0.U.-CgeAVXXbUEcbmFRjAS4UURT!ZNo0zq0Co!OvgroOByjwBHW8t3KloX6rdDAp2Ugpy4qIz84Xa2oyIPDUwvuEdb7xSYBPna74RRIGnOp5yp6D5Rb*GgdBEDxEZdEkCOdbwsC9JMLg6FlVnwgY6ubWIYKvULJmKOGKs*YXXXXXXXXXXXXXXXXX6QjBjjMY2ezziJDfga4TI*z9AMDW3*DSvSpGAkKtHG8bdFO4B7NItxLlMHiAEaVaOxSeqQuKAZVxy7N8kzKMcVNxTcjX1sbjfAZIznfKZXU*rQ4z64lTc6vMq*7hf774q3yFXQj2OMJoNXr6KUr9WcG!vrKHp1F5lVX!6defcYA8SgtXtMCFtrh3JrNsJJAAnUXNbXOgnGmwvdnZ5jxnYxegjVIn6!yv*tw$
[client_id] 8b4ba9dd-3ea5-4e5f-86f1-ddba2230dcf2
```
目前程序中已接入闪邮箱，可自行购买邮箱卡进行提取  

[预览](https://pik.bocchi2b.top)

### 注意
现在邀请新用户后，会有最高24小时的审核期，会员奖励不会立即结算  
![image](https://github.com/user-attachments/assets/29f795d0-bc14-48a7-884b-293c2701a613)

### 会员邀请主程序
![image](https://github.com/user-attachments/assets/d2d6704b-03af-46cb-9ad4-68ecf4c8b282)  

剩余邮箱为空时可以让用户手动输入邮箱进行邀请  
![image](https://github.com/user-attachments/assets/2b3aa86f-880b-404b-add6-59dccb20f9fd)  

### 代理池  
代理池项目:[ProxyPoolWithUI](https://github.com/OxOOo/ProxyPoolWithUI?tab=readme-ov-file)  
![image](https://github.com/user-attachments/assets/5c3fca09-6fb4-41d1-aeda-d69dc41d296b)


### 登录页面
请在登录页部分，更改默认账号密码  
![image](https://github.com/user-attachments/assets/2f890414-ceea-44f4-b07e-88de4f3c9ef0)

### 后台管理页面
包含一些配置开关，可以查看和管理已使用和未使用的邮箱  
![image](https://github.com/user-attachments/assets/c99085cd-cc94-495e-90fb-40936106502e)

![image](https://github.com/user-attachments/assets/d701587a-e496-4f61-a857-9a8a352aed90)  

### 添加邮箱页面
可以手动添加邮箱信息，也可以从下方邮箱卡购买网站中购买邮箱卡，注意是邮箱卡，不要买成邮箱  
把你的key填入后进行更新，输入数量后获取账号，可以自动添加到右方文本框中  
![image](https://github.com/user-attachments/assets/9962762c-8974-48f0-a9d1-973e4234def0)

### 卡密管理页面
支持增加、删除卡密，修改现有卡密  
![image](https://github.com/user-attachments/assets/795fafe7-820e-46d1-bbdd-5123bdac0a88)  

### 通知设置
[免费注册tiny](https://www.tiny.cloud/)  
复制api key  
![image](https://github.com/user-attachments/assets/4a125eb9-2de9-402a-a77b-d039cd703001)  
在```edit_announcement.html```中修改链接中的‘你的api密钥’为你的api key   
![image](https://github.com/user-attachments/assets/459bd39c-67d0-40d6-83f0-c2ab219cd7c2)  
在[域名白名单](https://www.tiny.cloud/my-account/domains/)中添加你的域名  
![image](https://github.com/user-attachments/assets/16867cf0-1fe7-4c89-a3a2-a56415b3cfe2)  
新增通知信息  
![image](https://github.com/user-attachments/assets/37852543-d88e-470f-93b8-86b14423f25e)  
支持编辑、删除现有的通知信息   
![image](https://github.com/user-attachments/assets/3c4e8565-3c1e-4e1a-9cb5-fd621554731d)

显示通知(只能启用一个通知，启用时会自动关闭其他通知)   
![image](https://github.com/user-attachments/assets/a4a7e9e9-84f6-47ed-9b3c-dd974d6bf216)




### ~~会员共享页面~~
~~只会显示近三天邀请成功的账号  
注意渲染时的密码是固定的，请确保与会员邀请程序中的密码一致~~
![image](https://github.com/user-attachments/assets/a3fc3c51-cc96-4917-9a9c-ddcec9478553)


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
自动获取验证码版本，运行 run.py
```
python run.py
```
手动获取验证码版本，运行 run_code.py
```
python run_code.py
```

