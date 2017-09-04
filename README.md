# python-webapp

[![python](https://img.shields.io/badge/python-3.6.2-blue.svg)](https://www.python.org/) [![license](https://img.shields.io/github/license/weileiming/python-webapp.svg)](https://github.com/WeiLeiming/python-webapp/blob/master/LICENSE)

这是[Python教程 - 廖雪峰的官方网站](https://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/001432170876125c96f6cc10717484baea0c6da9bee2be4000)中的一个博客实战项目，供学习使用。

## 项目结构

```
python-webapp/           <-- 根目录
|
+- backup/               <-- 备份目录
|
+- conf/                 <-- 配置文件
|
+- dist/                 <-- 打包目录
|
+- www/                  <-- Web目录，存放.py文件
|  |
|  +- static/            <-- 存放静态文件
|  |
|  +- templates/         <-- 存放模板文件
|
+- ios/                  <-- 存放iOS App工程
|
+- LICENSE               <-- LICENSE
```

## 运行

本地预览：

```
$ git clone https://github.com/WeiLeiming/python-webapp.git
$ cd python-webapp/www
$ mysql -u root -p < schema.sql
$ chmod +x pymonitor.py
$ ./pymonitor.py app.py
```

浏览器访问http://localhost:9000/

## 开发环境

- [Python](https://www.python.org/downloads/) 3.6.2
- [MySQL Community Server](https://dev.mysql.com/downloads/mysql/) 5.7.19
- 第三方库
  - [aiohttp](https://github.com/aio-libs/aiohttp) - Async http client/server framework (asyncio)
  - [jinja2](https://github.com/pallets/jinja) - a template engine written in pure Python
  - [aiomysql](https://github.com/aio-libs/aiomysql) - *aiomysql* is a library for accessing a MySQL database from the asyncio
  - [uikit](https://github.com/uikit/uikit) — A lightweight and modular front-end framework for developing fast and powerful web interfaces


## 开发工具

- [Sublime Text 3](https://www.waitsun.com/?s=Sublime+Text) — 代码编辑器
  - [Anaconda](https://github.com/DamnWidget/anaconda) - Anaconda turns your Sublime Text 3 in a full featured Python development IDE
- [Navicat Premium](https://www.waitsun.com/?s=Navicat+Premium) — 数据库客户端

## 总结

### 用户浏览页面：

- 首页：GET /
- 注册页：GET /register
- 登录页：GET /signin
- 日志详情页：GET /blog/{id}

### 管理页面：

- 评论列表页：GET /manage/comments
- 日志列表页：GET /manage/blogs
- 用户列表页：GET /manage/users
- 创建日志：GET /manage/blogs/create
- 修改日志：GET /manage/blogs/edit

### 后台API：

- 注册用户：POST /api/users
- 验证用户：POST /api/authenticate
- 获取用户：GET /api/users
- 退出用户：GET /signout
- 创建日志：POST /api/blogs
- 获取详情日志：GET /api/blogs/{id}
- 获取日志：GET /api/blogs
- 修改日志：POST /api/blogs/{id}
- 删除日志：POST /api/blogs/{id}/delete
- 创建评论：POST /api/blogs/{id}/comments
- 获取评论：GET /api/comments
- 删除评论：POST /api/comments/{id}/delete

## 参考

[廖雪峰老师的源码](https://github.com/michaelliao/awesome-python3-webapp)

[awesome-python](https://github.com/vinta/awesome-python)

