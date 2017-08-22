#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
configuration
"""

import config_default

__author__ = 'Will Wei'


class Dict(dict):
    """Simple dict but support access as x.y style."""
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value


# 合并默认配置和自定义配置
def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r


# dict转成Dict
def toDict(d):
    D = Dict()
    for k, v in d.items():
        # 如果是dict就接着转，否则直接赋值
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D


configs = config_default.configs


try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)
