#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
orm.py 的测试程序
数据库自建，不知道怎么建数据库的请自行查阅资料
"""

import asyncio
import orm
from orm import Model, IntegerField, StringField

__author__ = 'Will Wei'


class User(Model):
    """docstring for User"""
    __table__ = 'users'    # 表名如与类名不一致，需指定

    id = IntegerField('id', primary_key=True)    # 设定id为主键
    name = StringField('name')
    password = StringField('password')
    email = StringField('email')


async def connectDB(loop):
    # 指定所连数据库的设置
    # 对照自己的数据库进行设置，我这里只需设置这3个，其他按默认
    user = 'root'
    password = '111111'
    db = 'orm_test'
    await orm.create_pool(loop, user=user, password=password, db=db)


async def closeDB():
    await orm.destory_pool()


async def test_findAll(loop):
    await connectDB(loop)
    userlist = await User.findAll()
    print('test_findAll ==> all userlist: %s' % userlist)
    userlist = await User.findAll(orderBy='name', limit=2)    # orderBy: 按哪个字段排序, limit: 查找条数
    for index, user in enumerate(userlist):
        print('test_findAll ==> user%d: %s' % (index, user))
    await closeDB()


async def test_findNumber(loop):
    await connectDB(loop)
    id = await User.findNumber('id')
    name = await User.findNumber('name')
    password = await User.findNumber('password')
    email = await User.findNumber('email')
    print('test_findNumber ==> id: %s, name: %s, password: %s, email: %s' % (id, name, password, email))
    await closeDB()


async def test_find(loop):
    await connectDB(loop)
    user = await User.find('1')    # 根据主键查找
    print('test_find ==> user: %s' % user)
    await closeDB()


async def test_save(loop):
    await connectDB(loop)
    user = await User.find('5')    # 检查要存的主键是否存在
    if user is None:
        user = User(id=5, name='ZH', email='ZH@qj-vr.com', password='zh123')
        await user.save()
        print('test_save ==> user: %s', user)
    await closeDB()


async def test_update(loop):
    await connectDB(loop)
    user = await User.find('5')
    if user is not None:
        user.name = 'DY'
        await user.update()
        print('test_update ==> user: %s', user)
    await closeDB()


async def test_remove(loop):
    await connectDB(loop)
    user = await User.find('5')
    if user is not None:
        await user.remove()
        print('test_remove ==> user: %s', user)
    await closeDB()

loop = asyncio.get_event_loop()

loop.run_until_complete(test_findAll(loop))
loop.run_until_complete(test_findNumber(loop))
loop.run_until_complete(test_find(loop))
loop.run_until_complete(test_save(loop))
loop.run_until_complete(test_update(loop))
loop.run_until_complete(test_remove(loop))

loop.close()
