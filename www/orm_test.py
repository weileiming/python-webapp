#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Will Wei'

import asyncio
import orm

class User(Model):
	"""docstring for User"""
	__table__ = users

	id = IntegerField('id', primary_key=True)
	name = StringField('username')
	password = StringField('password')
	email = StringField('email')

async def connectDB(loop):
	pass

async def destoryDB():
	pass

async def test_findAll(loop):
	pass

async def test_findNumber(loop):
	pass

async def test_find(loop):
	pass

async def test_save(loop):
	pass

async def test_update(loop):
	pass

async def test_remove(loop):
	pass

loop = asyncio.get_event_loop()

loop.run_until_complete(test_findAll(loop))
loop.run_until_complete(test_findNumber(loop))
loop.run_until_complete(test_find(loop))
loop.run_until_complete(test_save(loop))
loop.run_until_complete(test_update(loop))
loop.run_until_complete(test_remove(loop))

loop.close()
