#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
coroweb.py 的测试程序
运行app_coroweb_test.py
"""

import asyncio
from coroweb import get, post

__author__ = 'Will Wei'


@get('/')
async def handler_url_blog(request):
    body = '<h1>Awesome</h1>'
    return body


@get('/greeting')
async def handler_url_greeting(*, name, request):
    body = '<h1>Awesome: /greeting %s</h1>' % name
    return body
