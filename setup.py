#!/usr/bin/env python
# coding: utf-8
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fd:
    long_description = fd.read()

setup(
    name = 'ChatRoom-jianjun',
    version = '1.1.2',
    author = 'jianjun',
    author_email = '910667956@qq.com',
    url = 'https://github.com/EVA-JianJun/ChatRoom',
    description = u'Python 聊天室!',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    packages = ["ChatRoom"],
    install_requires = [
        "rsa>=4.0",
        "bcrypt>=3.2.0",
    ],
    entry_points={
    },
)