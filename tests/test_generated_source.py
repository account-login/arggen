from functools import partial
import subprocess
import os
import re
from typing import Sequence, Dict

from arggen import (
    flag, count, arg, rest, ValueType, generate_files,
)


def file_time(filename: str):
    return os.stat(filename).st_mtime_ns


def cmd(*args):
    print('run_cmd: ', args)
    subprocess.check_call(args)


def get_env():
    CXX = os.environ.get('CXX', 'c++')
    CXXFLAGS = os.environ.get('CXXFLAGS', [])
    return locals()


def compile_source(env: Dict, source_file: str, output: str = None):
    assert source_file.endswith('.cpp')
    if output is None:
        output = re.sub(r'\.cpp$', '.o', source_file)
    if not os.path.exists(output) or file_time(output) < file_time(source_file):
        cmd(env['CXX'], *env['CXXFLAGS'], source_file, '-c', '-o', output)


def link_objects(env: Dict, objects: Sequence[str], output: str):
    cmd(env['CXX'], *env['CXXFLAGS'], *objects, '-o', output)


def test_generate_source():
    uai = [
        flag('--foo', '-f'),
        count('-v', '--verbose'),
        arg('--bar', '-b', type=ValueType.INT, default=123),
        arg('--qwer'),
        arg('haha', name='hahaha'),
        rest('asdf')
    ]
    generate_files(dict(MyOption=uai), 'tests/test')

    env = get_env()
    env['CXXFLAGS'].extend(['-std=c++11', '-Wall', '-Wextra'])
    compile_source(env, 'tests/catch.cpp')

    env['CXXFLAGS'].append('--coverage')
    compile_source(env, 'tests/test.cpp')
    compile_source(env, 'tests/test_main.cpp')
    link_objects(env, ['tests/test.o', 'tests/test_main.o', 'tests/catch.o'], 'tests/test')

    cmd('tests/test', '-d', 'yes', '-s')
