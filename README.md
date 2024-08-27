


# 项目说明

## pikpak会员自动邀请程序1.2，python编写
## 原作者：B站纸鸢的花语
## 二改作者：非雨 
GitHub：[https://github.com/liuxianlu/pikpak_werbio](https://github.com/liuxianlu/pikpak_werbio)

### 注意
现在邀请新用户后，会有最高24小时的审核期，会员奖励不会立即结算  
![image](https://github.com/user-attachments/assets/29f795d0-bc14-48a7-884b-293c2701a613)


### 登录页面
请在app.py的登录页部分，更改账号密码  
![image](https://github.com/user-attachments/assets/2f890414-ceea-44f4-b07e-88de4f3c9ef0)

### 邮箱管理页面
可以查看和管理已使用和未使用的邮箱  
![image](https://github.com/user-attachments/assets/3c3eb2ca-1b94-4d38-ac18-9e2afdf304ce)
![image](https://github.com/user-attachments/assets/275fc323-c96b-496c-899d-dbfeed15653a)



### 添加邮箱页面
https://example.com/bulk_add  
可以手动添加邮箱信息，也可以从下方邮箱卡购买网站中购买邮箱卡，注意是邮箱卡，不要买成邮箱  
把你的key填入后进行更新，输入数量后获取账号，可以自动添加到右方文本框中  
![image](https://github.com/user-attachments/assets/ea7c6b0d-10f3-450e-8921-448108f4ddcb)

### 会员共享页面
https://example.com/public_email  
只会显示近三天邀请成功的账号  
注意渲染时的密码是固定的，请确保与会员邀请程序中的密码一致
![image](https://github.com/user-attachments/assets/a3fc3c51-cc96-4917-9a9c-ddcec9478553)

### 是否公开
所有页面默认都是需要登陆后查看的，可以自行独立出部分页面  
以共享页面为例：  
只要删除选中的这两行即可  
![image](https://github.com/user-attachments/assets/253f1364-595c-4d00-8561-095da1587e0a)

### 邮箱接口
邮箱卡购买地址:
- [https://shanyouxiang.com/](https://shanyouxiang.com/)

## 代码详情
pik.py 为会员邀请程序  
app.py 为邮箱文本管理程序

## 运行
安装依赖 
```
pip install -r requirements.txt
```  

分别运行 app.py 和 pik.py  
```
python app.py
python pik.py
```
