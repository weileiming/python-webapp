#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
default configuration
"""

__author__ = 'Will Wei'


configs = {
    'debug': True,
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '111111',
        'db': 'awesome'
    },
    'session': {
        'secret': 'Awesome'
    }
}
