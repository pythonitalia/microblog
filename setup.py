#!/usr/bin/env python

from distutils.core import setup

import os
import os.path

def recurse(path):
    B = 'microblog'
    output = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(B, path)):
        for d in filter(lambda x: x[0] == '.', dirnames):
            dirnames.remove(d)
        for f in filenames:
            output.append(os.path.join(dirpath, f)[len(B)+1:])
    return output

setup(name='microblog',
    version='0.1.3',
    description='django microblog',
    author='dvd',
    author_email='dvd@develer.com',
    packages=[
        'microblog',
        'microblog.management',
        'microblog.management.commands',
        'microblog.migrations',
        'microblog.templatetags',
        'microblog.utils',
    ],
    package_data={
        'microblog': sum(map(recurse, ('deps', 'locale', 'static', 'templates')), []),
    },
    install_requires=[
        'lxml',
        'django_pingback',
        'html2text',
        'python-twitter',
        'django-taggit',
        'fancy_tag',
    ],
)
