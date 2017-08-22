#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
url handlers
"""

import asyncio
from coroweb import get, post
from models import User, Comment, Blog, next_id

__author__ = 'Will Wei'


@get('/')
async def index(request):
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }
