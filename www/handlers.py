#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
url handlers
"""

import asyncio
import time
import hashlib
import re
import json
import logging
import markdown2
from aiohttp import web
from coroweb import get, post
from models import User, Comment, Blog, next_id
from apis import Page, APIError, APIValueError, APIResourceNotFoundError, APIPermissionError
from config import configs

__author__ = 'Will Wei'

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

"""
Tool method
"""


# 检查是否有管理权限
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


# 获取页码
def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


# 文本转html
def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


"""
Cookie
"""


# 通过用户信息计算cookie
def user2cookie(user, max_age):
    """
    Generate cookie str by user.
    "用户id" + "过期时间" + SHA1("用户id" + "用户口令" + "过期时间" + "SecretKey")
    """
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.password, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


# 通过cookie获取用户信息
async def cookie2user(cookie_str):
    """
    Parse cookie and load user if cookie is valid.
    "用户id" + "过期时间" + SHA1("用户id" + "用户口令" + "过期时间" + "SecretKey")
    """
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.password, expires, _COOKIE_KEY)
        # 验证SHA1值
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.password = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


"""
页面
"""


# 首页
@get('/')
async def index(request, *, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num, page_index)
    if page == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return{
        '__template__': 'blogs.html',
        'page': page,
        'blogs': blogs,
        '__user__': request.__user__
    }


# 注册
@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }


# 登录
@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }


# 日志详情
@get('/blog/{id}')
async def get_blog(request, *, id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments,
        '__user__': request.__user__
    }


# 创建日志
@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs',
        '__user__': request.__user__
    }


# 日志编辑
@get('/manage/blogs/edit')
def manage_edit_blog(request, *, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id,
        '__user__': request.__user__
    }


# 管理
@get('/manage/')
def manage():
    return 'redirect:/manage/comments'


# 日志列表
@get('/manage/blogs')
def manage_blogs(request, *, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page),
        '__user__': request.__user__
    }


# 管理评论
@get('/manage/comments')
def manage_comments(request, *, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page),
        '__user__': request.__user__
    }


# 用户管理
@get('/manage/users')
def manage_users(request, *, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page),
        '__user__': request.__user__
    }


"""
Api
"""


# 获取用户信息
@get('/api/users')
async def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = await User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())
    users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)


# 用户注册
@post('/api/users')
async def api_register_user(*, email, name, passwd):
    # name.strip()删除空白字符
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('password')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    # 根据用户id:密码，进行SHA1计算之后再存数据库
    sha1_password = '%s:%s' % (uid, passwd)
    encrypt_password = hashlib.sha1(sha1_password.encode('utf-8')).hexdigest()
    # 头像用了Gravatar，如果以前注册过就会有这个全球头像
    image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest()
    user = User(id=uid, name=name.strip(), email=email, password=encrypt_password, image=image)
    await user.save()
    # make session cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


# 用户验证登录
@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('password', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check password:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.password != sha1.hexdigest():
        raise APIValueError('password', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


# 用户退出
@get('/signout')
def signout(request):
    # 获取上一个页面
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    # 设置cookie最大时间，删除cookie
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r


# 创建日志
@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    user = request.__user__
    blog = Blog(
        user_id=user.id,
        user_name=user.name,
        user_image=user.image,
        name=name.strip(),
        summary=summary.strip(),
        content=content.strip())
    await blog.save()
    return blog


# 获取某篇日志
@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog


# 获取页日志
@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)


# 更新日志
@post('/api/blogs/{id}')
async def api_update_blog(id,request,*,name,summary,content):
    check_admin(request)
    blog = await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary can not be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog


# 删除日志
@post('/api/blogs/{id}/delete')
async def api_delete_blog(request, *, id):
    check_admin(request)
    blog = await Blog.find(id)
    await blog.remove()
    return dict(id=id)


# 获取页评论
@get('/api/comments')
async def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = await Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = await Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)


# 获取某篇日志评论
@post('/api/blogs/{id}/comments')
async def api_create_comments(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(
        blog_id=blog.id,
        user_id=user.id,
        user_name=user.name,
        user_image=user.image,
        content=content.strip())
    await comment.save()
    return comment


# 删除评论
@post('/api/comments/{id}/delete')
async def api_delete_comments(id, request):
    check_admin(request)
    c = await Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    await c.remove()
    return dict(id=id)
