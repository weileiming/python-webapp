#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Will Wei'

'''
async web application.
'''

import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(content_type='text/html', body=b'<h1>Awesome</h1>')    # 增加content_type='text/html'，不然访问会直接下载

async def init(loop):   # async替代@asyncio.coroutine装饰器，表示这是个异步运行的函数
    app = web.Application(loop=loop)    # loop=loop是处理用户参数用的，访问量少不添加代码照样运行，高并发时就会出问题
    app.router.add_route('GET', '/', index)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)   # await替代yield from，表示要放入loop中进行的异步操作
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()    # 获取asyncio event loop
loop.run_until_complete(init(loop))    # 用asyncio event loop来异步运行init()
loop.run_forever()
