#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Will Wei'

import asyncio
import aiomysql
import logging


# SQL日志输出
def log(sql, args=()):
    logging.info('SQL: %s' % sql)


# 创建全局连接池
async def create_pool(loop, **kw):
    logging.info('start create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


# 销毁连接池
async def destory_pool():
    global __pool
    if __pool is not None:
        __pool.close()
        await __pool.wait_closed()


# SELECT语句
async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs


# INSERT、UPDATE、DELETE语句
# 3种SQL执行所需参数一样，定义通用执行函数
async def execute(sql, args, autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected


# 工具函数，构建insert语句占位符
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)


# Field类，保存表的字段名，字段类型，主键，默认值
class Field(object):
    """docstring for Field"""
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        # 表名, 字段名: 字段类型
        return '<%s, %s: %s>' % (self.__class__.__name__, self.name, self.column_type)


# 映射数据库varchar类型
class StringField(Field):
    """docstring for StringField"""
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


# 映射数据库boolean类型
class BooleanField(Field):
    """docstring for BooleanField"""
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


# 映射数据库bigint类型
class IntegerField(Field):
    """docstring for IntegerField"""
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


# 映射数据库real类型
class FloatField(Field):
    """docstring for FloatField"""
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


# 映射数据库text类型
class TextField(Field):
    """docstring for TextField"""
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


# 定义Model的元类，继承自type
# 为一个数据库表映射成一个封装的类做准备，读取具体子类的映射信息
class ModelMetaclass(type):
    """docstring for ModelMetaclass"""
    # __new__控制__init__的执行，所以在其执行之前
    # cls: 代表要__init__的类，此参数在实例化时由Python解释器自动提供
    # bases：代表继承父类的集合
    # attrs：类的方法集合
    def __new__(cls, name, bases, attrs):
        # 排除Model类本身
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取表名
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名
        mappings = dict()
        fields = []
        primaryKey = None
        # key表示字段名，value表示属性
        for key, value in attrs.items():
            if isinstance(value, Field):
                logging.info('found mapping: %s ==> %s' % (key, value))
                mappings[key] = value
                if value.primary_key:
                    # 主键
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field: %s' % key)
                    primaryKey = key
                else:
                    fields.append(key)
        if not primaryKey:
            raise StandardError('Primary key not found.')
        for key in mappings.keys():
            attrs.pop(key)

        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        # 保存属性和列的映射关系
        attrs['__mappings__'] = mappings
        # 表名
        attrs['__table__'] = tableName
        # 主键属性名
        attrs['__primaty_key__'] = primaryKey
        # 除主键外的属性名
        attrs['__fields__'] = fields
        # 构造默认的CRUD操作语句
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


# 定义所有ORM映射的基类
# Model类的子类映射数据库表
class Model(dict, metaclass=ModelMetaclass):
    """docstring for Model"""
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    # 类方法
    # 根据where条件查找
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    # 类方法
    # 根据where条件查找，但返回整数
    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    # 类方法
    # 根据主键查找
    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primaty_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    # 实例方法
    # 保存
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primaty_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    # 实例方法
    # 更新
    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primaty_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    # 实例方法
    # 删除
    async def remove(self):
        args = [self.getValue(self.__primaty_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('faild to remove by primary key: affected rows: %s' % rows)
