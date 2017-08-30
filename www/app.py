#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
async web application.
"""

import asyncio
import os
import json
import time
import orm
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from coroweb import add_routes, add_static
from config import configs
from handlers import cookie2user, COOKIE_NAME
import logging
# 日志级别关系：CRITICAL > ERROR > WARNING > INFO > DEBUG > NOTSET
logging.basicConfig(level=logging.INFO)

__author__ = 'Will Wei'


# 初始化jinja2，配置jinja2环境
def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(
        # 是否自动转义xml/html
        autoescape=kw.get('autoescape', True),
        # 代码块开始结束标志
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        # 变量开始结束标志
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        # 模板修改后，下次请求是否重新加载
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 templates path: %s' % path)
    # 环境配置
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    # app中添加__templating__保存env，这样app就知道要去哪找模板，怎么解析模板
    app['__templating__'] = env


# 日志处理，请求时输出请求方法和路径
async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return (await handler(request))
    return logger


# 利用middle在处理URL之前，把cookie解析出来，并将登录用户绑定到request对象上，后续的URL处理函数就可以直接拿到登录用户
async def auth_factory(app, handler):
    async def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            # 验证cookie，并得到用户信息
            user = await cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
        # # 如果请求路径是管理页面，但是用户不是管理员，将重定向到登陆页面
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return (await handler(request))
    return auth


# 数据处理，请求为post时起作用
async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data


# 响应处理
# request处理流水线顺序是：logger_factory->response_factory->RequestHandler().__call__->get或post->handler
# 对应的response处理流水线顺序是:
# 1. 由handler构造出要返回的具体对象
# 2. 然后在这个返回的对象上加上'__method__'和'__route__'属性，以标识别这个对象
# 3. RequestHandler目的就是从request的content中获取必要的参数，调用URL处理函数,然后把结果返回给response_factory
# 4. response_factory在拿到经过处理后的对象，经过一系列类型判断，构造出正确web.Response对象，以正确的方式返回给客户端
# 在这个过程中，只关心handler的处理，其他的都走统一通道，如果需要差异化处理，就在通道中选择适合的地方添加处理代码。
# 注：在response_factory中应用了jinja2来渲染模板文件
async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        # 如果相应结果为StreamResponse，直接返回
        # StreamResponse是aiohttp定义response的基类
        if isinstance(r, web.StreamResponse):
            return r
        # 如果相应结果为字节流，则将其作为应答的body部分，并设置响应类型为流型
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        # 如果响应结果为字符串
        if isinstance(r, str):
            # 判断响应结果是否为重定向，如果是，返回重定向后的结果
            if r.startswith('redirect:'):
                # 即把r字符串之前的"redirect:"去掉
                return web.HTTPFound(r[9:])
            # 如果不是，以utf8对其编码，并设置响应类型为html型
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        # 如果响应结果是字典，则获取jinja2模板信息，此处为jinja2.env
        if isinstance(r, dict):
            template = r.get('__template__')
            # 若不存在对应模板，则将字典调整为json格式返回，并设置响应类型为json
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        # 如果响应结果为整数型，且在100和600之间
        # 此时r为状态码
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        # 如果响应结果为长度为2的元组
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            # 元组第一个值为整数型且在100和600之间
            # 则t为http状态码，m为错误描述，返回状态码和错误描述
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # 默认以字符串形式返回响应结果，设置类型为普通文本
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


# 时间过滤器，作用是返回日志创建的时间，用于显示在日志标题下面
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


async def init(loop):   # async替代@asyncio.coroutine装饰器，表示这是个异步运行的函数
    await orm.create_pool(loop=loop, **configs.db)
    # loop=loop是处理用户参数用的，访问量少不添加代码照样运行，高并发时就会出问题
    # middlewares(中间件)设置3个中间处理函数(装饰器)
    app = web.Application(loop=loop, middlewares=[logger_factory, auth_factory, response_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)   # await替代yield from，表示要放入loop中进行的异步操作
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()    # 获取asyncio event loop
loop.run_until_complete(init(loop))    # 用asyncio event loop来异步运行init()
loop.run_forever()
