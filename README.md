


# 项目说明

## pikpak会员自动邀请程序1.2，python编写
## 原作者：B站纸鸢的花语
## 二改作者：非雨 
GitHub：[https://github.com/liuxianlu/pikpak_werbio](https://github.com/liuxianlu/pikpak_werbio)






















## -------------------------------------v1.1版本------------------------------------------------------
# pikpak_werbio v1.1


## 项目说明

### pikpak会员自动邀请程序，python编写, 次日掉会员版本
### 原作者：B站纸鸢的花语
### 二改作者：非雨 
GitHub：[https://github.com/liuxianlu/pikpak_werbio](https://github.com/liuxianlu/pikpak_werbio)

### 更新内容

1. 增加3个API邮箱接口（将接口卡密1，2，3替换为实际购买的邮箱卡密）
2. 增加卡密验证（可自定义卡密及使用次数 有卡密的用户才能执行邀请程序） 、可直接部署在网页运行


### 已知问题

运行两个小时后会出现`add_days`异常失败，部署在宝塔面板的可设置为定时重启项目即可解决！

### 声明

纸鸢花的花语所提供的任何资源或素材代码，仅供学习交流和技术分析，严禁用于任何商业牟利行为（包括但不限于引流用户加入社群，利用免费学习素材牟利贩卖，冒充原作者盗用引流增加用户数等）。

出现任何后果自行承担，与资源的分享者没有任何关系和责任，如出现违反规定侵权行为，原作者有权对违规者进行版权控诉处理。

### 如何运行

1. 下载`werbio.py`文件到本地用 Python 运行。
2. 运行后提示什么错误就安装什么库，例如: `pip install requests`。
3. 将接口卡密1，2，3替换为实际购买的邮箱卡密。将card_keys代码中卡密及使用次数修改为自己喜欢的卡密
4. 运行成功后复制网址到浏览器打开，输入邀请码 例：123456 卡密 例：0727-0827-3382SJ2SJ 即可运行在网页执行邀请程序，可搭建部署在服务器运行。


修改 key1 = "接口卡密1" 为实际购买的邮箱卡 key2 = "接口卡密2" 为实际购买的邮箱卡  key3 = "接口卡密3" 为实际购买的邮箱卡 
   
自己修改、新增代码中的卡密及使用次数 
```python
card_keys = {
"0727-0827-3382SJ2SJ": 10000,
"0727-0728-DDMMD2293": 10
}
```

### 邮箱接口
邮箱卡购买地址:
- [https://shanyouxiang.com/](https://shanyouxiang.com/)
- [https://zhanghaoya.com/](https://zhanghaoya.com/)
- [https://atufn.com/](https://atufn.com/)




