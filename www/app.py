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
import logging
logging.basicConfig(level=logging.INFO)

__author__ = 'Will Wei'


def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 templates path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


async def init(loop):   # async替代@asyncio.coroutine装饰器，表示这是个异步运行的函数
    app = web.Application(loop=loop)    # loop=loop是处理用户参数用的，访问量少不添加代码照样运行，高并发时就会出问题
    app.router.add_route('GET', '/', index)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)   # await替代yield from，表示要放入loop中进行的异步操作
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()    # 获取asyncio event loop
loop.run_until_complete(init(loop))    # 用asyncio event loop来异步运行init()
loop.run_forever()
