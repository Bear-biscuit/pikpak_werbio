


# 项目说明

## pikpak会员自动邀请程序
## 原作者：B站纸鸢的花语
倒卖 牡蛎😘~~~


### 注意
现在邀请新用户后，会有最高24小时的审核期，会员奖励不会立即结算  
![image](https://github.com/user-attachments/assets/29f795d0-bc14-48a7-884b-293c2701a613)

### 会员邀请主程序
![image](https://github.com/user-attachments/assets/d76b6a18-b12d-42d3-9540-912ffa68f200)


### 代理池  
代理池项目:[ProxyPoolWithUI](https://github.com/OxOOo/ProxyPoolWithUI?tab=readme-ov-file)  
![image](https://github.com/user-attachments/assets/5c3fca09-6fb4-41d1-aeda-d69dc41d296b)



### 登录页面
请在登录页部分，更改默认账号密码  
![image](https://github.com/user-attachments/assets/2f890414-ceea-44f4-b07e-88de4f3c9ef0)

### 邮箱管理页面
可以查看和管理已使用和未使用的邮箱  
![image](https://github.com/user-attachments/assets/6d37f883-857a-458b-95a0-e2b1da9f3558)
![image](https://github.com/user-attachments/assets/f3628ced-bb93-44b3-8987-4b6f6cebf9aa)
邮箱测活，会自动删除失效的邮箱
![image](https://github.com/user-attachments/assets/241518f1-c608-446f-829d-aebd7f5e951e)

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
运行 run.py
```
python run.py
```
