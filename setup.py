#!/usr/bin/env python
# coding: utf-8
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fd:
    long_description = fd.read()

setup(
    name = 'ChatRoom',
    version = '1.0.0',
    author = 'jianjun',
    author_email = '910667956@qq.com',
    url = 'https://github.com/EVA-JianJun/ChatRoom',
    description = u'Python 聊天室!',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    packages = ["ChatRoom"],
    install_requires = [],
    entry_points={
    },
)