import pytest

from arggen import (
    ArgError, ArgType, ArgInfo, ValueType,
    flag, count, arg, rest,
    process_config, parse_config_string,
)


SAMPLE_CONFIG_STRING = '''[
    flag('--foo', '-f'),
    count('-v', '--verbose'),
    arg('--bar', '-b', type=ValueType.INT),
    arg('haha', name='hahaha', default='abc'),
    rest('asdf')
]
'''
SAMPLE_CONFIG = eval(SAMPLE_CONFIG_STRING)


foo = ArgInfo(
    name='foo', options=('--foo', '-f'), arg_type=ArgType.BOOL,
    value_type=ValueType.BOOL, default=False,
)
verbose = ArgInfo(
    name='verbose', options=('-v', '--verbose'), arg_type=ArgType.COUNT,
    value_type=ValueType.INT, default=None,
)
bar = ArgInfo(
    name='bar', options=('--bar', '-b'), arg_type=ArgType.ONE,
    value_type=ValueType.INT, default=None,
)
haha = ArgInfo(
    name='hahaha', options=('haha',), arg_type=ArgType.ONE,
    value_type=ValueType.STRING, default='abc',
)
asdf = ArgInfo(
    name='asdf', options=('asdf',), arg_type=ArgType.REST,
    value_type=ValueType.STRING, default=None,
)

EXPECTED_CONFIG = [foo, verbose, bar, haha, asdf]


def test_basic():
    assert process_config(SAMPLE_CONFIG) == EXPECTED_CONFIG


def test_invalid_user_arg_info():
    def E(*args):
        with pytest.raises(ArgError):
            process_config(args)

    # invalid name
    E(arg('1ab'))
    E(arg('--'))
    E(arg('-'))
    E(arg('--a_b'))
    E(arg('--0-b'))

    # can not determine name
    E(arg('--asfd', '--qwer'))

    # multiple rest
    E(rest('asfd'), rest('aaa'))

    # duplicated option
    E(arg('--asdf', '-a'), arg('--wqer', '-a'))

    # duplicated name
    E(arg('asdf'), arg('--asdf'))

    # invalid param
    E(count('-v', default=1))
    E(flag('-v', default=1))
    E(rest('asdf', default=1))
    E(count('-v', type=ValueType.BOOL))
    E(flag('asfd', type=ValueType.BOOL))

    # positional args with default value is not on tail
    E(arg('a'), arg('b', default='b'), arg('c'))


def test_parse_config_string():
    input = f'''
foo = 123
haha = [(), 124]
MyOption = {SAMPLE_CONFIG_STRING}
    '''
    configs = parse_config_string(input)
    assert len(configs) == 1
    assert process_config(configs['MyOption']) == EXPECTED_CONFIG
