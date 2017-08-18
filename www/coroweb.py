#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
web framework
"""

import asyncio
import os
import inspect
import functools
import logging

from urllib import parse
from aiohttp import web
from apis import APIError

__author__ = 'Will Wei'


# get装饰器，添加请求方法和请求路径
# 函数通过@get(path)装饰就附带URL信息
def get(path):
    # Define decorator @get('/path')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator


# post装饰器，添加请求方法和请求路径
# 函数通过@post(path)装饰就附带URL信息
def post(path):
    # Define decorator @post('/path')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = 'path'
        return wrapper
    return decorator


'''
使用inspect模块signature方法获取函数的参数
Parameter类型：
POSITIONAL_ONLY             位置参数
POSITIONAL_OR_KEYWORD       关键字或位置参数
VAR_POSITIONAL              位置参数tuple，相当于*args
KEYWORD_ONLY                关键字参数
VAR_KEYWORD                 关键字参数dict，相当于**kwargs
'''


# 创建几个函数对URL处理函数参数做一些处理判断
# 获取没有默认值的关键字参数的tuple
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


# 获取关键字参数的tuple
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


# 判断是否含有关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


# 判断是否含有可变的关键字参数(**kw)
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


# 判断是否含有名为request的参数，且该参数为最后一个关键字或位置参数
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        # 如果为真，则param为POSITIONAL_OR_KEYWORD
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found


# 从URL处理函数中分析需要接收的参数，从request中获取必要的参数
# 调用URL函数，然后把结果转换为web.Response
class RequestHandler(object):
    """docstring for RequestHandler"""

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    # 定义__call__参数后，其实例可以被视为函数
    async def __call__(self, request):
        kw = None  # 用于保存参数
        # 判断是否存在参数
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            # POST
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-type.')
                ct = request.content_type.lower()
                # application/json表示消息主体是序列化后的json字符串
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(text='JSON body must be object.')
                    kw = params
                # 消息主体是表单
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
            # GET
            if request.method == 'GET':
                # query_string表示url中的查询字符串，即?后面的请求参数
                # https://www.baidu.com/s?wd=python&ie=utf-8
                # wd=python&ie=utf-8即为查询字符串
                qs = request.query_string
                if qs:
                    kw = dict()
                    # urllib.parse.parse_qs(qs, keep_blank_values=False, strict_parsing=False, encoding='utf-8', errors='replace')
                    # 解析一个类型为application/x-www-form-urlencoded的查询字符串
                    # 返回一个dict，k是查询变量名称，值是每个名称的值列表
                    # 如{'wd': ['python'], 'ie', [utf-8]}
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unamed kw:
                # 移除kw中不是fn关键字参数的项
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            # kw中加入match_info中的值
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        # 检查kw是否包含全部没有默认值的关键字参数
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        # 调用handler，并返回response
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


# 添加静态文件夹路径
def add_static(app):
    # 提取同目录下的static目录
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    # 将该目录加入应用的路由管理器中
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))


# 把URL请求处理函数注册到app
def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    # 如果fn不是协程和生成器，将它变成协程
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info(
        'add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))


# 批量注册URL函数
def add_routes(app, module_name):
    # str.rfind(sub[, start[, end]])
    # 返回发现子字符串中最高索引，失败返回-1
    n = module_name.rfind('.')
    if n == (-1):
        # 在当前目录
        mod = __import__(module_name, globals(), locals())
    else:
        # 去除模块名称'.'前面的，然后导入
        # 如aaa.bbb，取bbb
        name = module_name[n + 1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    # dir()没有参数时返回当前本地作用域中的名称列表
    # 有参数时返回该对象的有效属性列表
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)
