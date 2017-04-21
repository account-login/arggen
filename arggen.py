import enum
import json
import re
from typing import Set, Sequence, Tuple, Dict, List


class ArgError(Exception):
    pass


class ArgType(enum.Enum):
    BOOL = object()
    COUNT = object()
    ONE = object()
    REST = object()


class ValueType(enum.Enum):
    STRING = object()
    INT = object()
    BOOL = object()


def make_func(arg_type: ArgType):
    def func(*args: str, **kwargs):
        return arg_type, args, kwargs
    return func


flag = make_func(ArgType.BOOL)
count = make_func(ArgType.COUNT)
arg = make_func(ArgType.ONE)
rest = make_func(ArgType.REST)


UserArgInfo = Tuple[ArgType, Sequence[str], Dict]


class ArgInfo:
    def __init__(
            self, *,
            name: str, options: Sequence[str], arg_type: ArgType,
            value_type: ValueType, default
    ):
        self.name = name
        self.options = options
        self.arg_type = arg_type
        self.value_type = value_type
        self.default = default

    def to_tuple(self):
        return self.name, self.options, self.arg_type, self.value_type, self.default

    def __repr__(self):
        return "<ArgInfo name=%s options=%s arg_type=%s value_type=%s default=%s>" % self.to_tuple()

    def __hash__(self):
        return hash(self.to_tuple())

    def __eq__(self, other: 'ArgInfo'):
        return self.to_tuple() == other.to_tuple()

    def __ne__(self, other):
        return not (self == other)


def get_option_name(options: Sequence[str], param: Dict) -> str:
    name = param.get('name')
    if name is not None:
        return name

    if is_position_option(options):
        return options[0]

    for opt in options:
        if opt.startswith('--'):
            if name is not None:
                raise ArgError('multiple long option')
            name = long_option_to_name(opt)
    return name


def verify_option_string(argname: str):
    if re.fullmatch(r'-[a-zA-Z0-9]', argname):
        return
    else:
        long_option_to_name(argname)


def long_option_to_name(argname: str):
    if not argname.startswith('--') or len(argname) <= 2:
        raise ArgError('bad long arg %s' % (argname,))
    argname = argname[2:]

    words = argname.split('-')
    assert len(words) >= 1
    for wd in words:
        if not re.fullmatch('[a-zA-Z0-9]+', wd):
            raise ArgError('bad word %s' % (wd,))
    if not re.fullmatch('[a-zA-Z]', words[0][0]):
        raise ArgError('bad leading word %s' % (words[0],))

    return '_'.join(words)


def is_position_option(options):
    return len(options) == 1 and re.fullmatch('[a-zA-Z][a-zA-Z0-9_]*', options[0])


def get_value_type_and_default(name: str, arg_type: ArgType, param: Dict):
    if arg_type == ArgType.BOOL:
        value_type = ValueType.BOOL
        default = False
    elif arg_type == ArgType.COUNT:
        value_type = ValueType.INT
        default = param.get('default', None)
    elif arg_type == ArgType.ONE:
        value_type = param.get('type', ValueType.STRING)
        default = param.get('default', None)
    elif arg_type == ArgType.REST:
        value_type = param.get('type', ValueType.STRING)
        if value_type not in (ValueType.STRING, ValueType.INT):
            raise ArgError('only string & int are allowed in rest option')
        default = None
    else:
        assert False, 'unreachable'

    if arg_type in (ArgType.BOOL, ArgType.COUNT, ArgType.REST):
        if 'default' in param:
            raise ArgError('"default" param not allowed in %s' % (name,))
    if arg_type in (ArgType.BOOL, ArgType.COUNT):
        if 'type' in param:
            raise ArgError('"type" param not allowed in %s' % (name,))

    return value_type, default


def process_user_arg_info(argsinfo: Sequence[UserArgInfo]):
    has_rest = False
    options_set = set()         # type: Set[str]
    name_set = set()            # type: Set[str]
    arginfo_list = []           # type: List[ArgInfo]

    for arg_type, options, param in argsinfo:
        for opt in options:
            if opt in options_set:
                raise ArgError('duplicated option %s' % (opt,))
            options_set.add(opt)

        if not is_position_option(options):
            for opt in options:
                verify_option_string(opt)

        name = get_option_name(options, param)
        if name in name_set:
            raise ArgError('duplicated option name %s' % (name,))
        name_set.add(name)

        if arg_type == ArgType.REST:
            if has_rest:
                raise ArgError('multiple rest arg_type')
            has_rest = True

        value_type, default = get_value_type_and_default(name, arg_type, param)

        ai = ArgInfo(
            name=name, options=options,
            arg_type=arg_type, value_type=value_type, default=default,
        )

        arginfo_list.append(ai)

    return arginfo_list


value_type_to_cxx_type = {
    ValueType.STRING: 'std::string',
    ValueType.INT: 'int',
    ValueType.BOOL: 'bool',
}


class BadSourceStructure(Exception):
    pass


class Label:
    def __init__(self, text):
        self.text = text


class BaseNode:
    def __init__(self):
        self.children = []
        self.parent = None

    def add_child(self, child):
        self.children.append(child)
        return self

    def indent(self, level: int):
        return '    ' * level

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.children == other.children

    def __ne__(self, other):
        return not (self == other)


class Body(BaseNode):
    def to_source_body(self, level: int):
        for child in self.children:
            if isinstance(child, str):
                if child:
                    yield self.indent(level) + child
                else:
                    yield ''    # empty line
            elif isinstance(child, Label):
                yield self.indent(level - 1) + child.text
            else:
                yield from child.to_source(level)


class Root(Body):
    def to_source(self, level: int):
        yield from self.to_source_body(level)


class Block(Body):
    def __init__(self, head: str, trailing_semicolon=False):
        super().__init__()
        self.head = head
        self.trailing_semicolon = trailing_semicolon

    def to_source(self, level: int):
        yield self.indent(level) + self.head + ' {'
        yield from self.to_source_body(level + 1)
        if self.trailing_semicolon:
            yield self.indent(level) + '};'
        else:
            yield self.indent(level) + '}'

    def __eq__(self, other):
        return super().__eq__(other) and self.head == other.head


class Condition(BaseNode):
    def to_source(self, level: int):
        if not self.children:
            raise BadSourceStructure('Condition node has no children')
        if not isinstance(self.children[0], If):
            raise BadSourceStructure('expect if, got %r' % (self.children[0],))

        yield self.indent(level) + 'if (%s) {' % self.children[0].cond
        yield from self.children[0].to_source_body(level + 1)

        for elseif in self.children[1:-1]:
            if not isinstance(elseif, ElseIf):
                raise BadSourceStructure(f'expect elseif, got {elseif!r}')
            yield self.indent(level) + '} else if (%s) {' % (elseif.cond,)
            yield from elseif.to_source_body(level + 1)

        if len(self.children) > 1:
            last = self.children[-1]
            if isinstance(last, ElseIf):
                yield self.indent(level) + '} else if (%s) {' % (last.cond,)
                yield from last.to_source_body(level + 1)
            elif isinstance(last, Else):
                yield self.indent(level) + '} else {'
                yield from last.to_source_body(level + 1)
            else:
                raise BadSourceStructure(f'expect elseif|else, got {last!r}')

        yield self.indent(level) + '}'


class If(Block):
    def __init__(self, cond: str):
        super().__init__(f'if ({cond})')
        self.cond = cond

    def __eq__(self, other):
        return super().__eq__(other) and self.cond == other.cond


class ElseIf(Body):
    def __init__(self, cond: str):
        super().__init__()
        self.cond = cond

    def __eq__(self, other):
        return super().__eq__(other) and self.cond == other.cond


class Else(Body):
    pass


# noinspection PyPep8Naming
class Context:
    def __init__(self):
        self.root = Root()
        self.cur = self.root

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cur = self.cur.parent

    def add_child(self, child):
        self.cur.add_child(child)

    def add_cur(self, child):
        self.add_child(child)
        child.parent = self.cur
        self.cur = child
        return self

    def BLOCK(self, head: str, trailing_semiconlon=False):
        return self.add_cur(Block(head, trailing_semicolon=trailing_semiconlon))

    def CONDITION(self):
        return self.add_cur(Condition())

    def IF(self, cond: str):
        return self.add_cur(If(cond))

    def ELSEIF(self, cond: str):
        return self.add_cur(ElseIf(cond))

    def MATCH(self, cond: str):
        if len(self.cur.children) == 0:
            return self.IF(cond)
        else:
            return self.ELSEIF(cond)

    def ELSE(self):
        return self.add_cur(Else())


def collect_node(gen) -> Root:
    ctx = Context()
    for stmt in gen(ctx):
        ctx.add_child(stmt)

    return ctx.root


def repr_c_string(string: str):
    return json.dumps(string)


def struct_gen(ctx: Context, struct_name: str, argsinfo: Sequence[ArgInfo]):
    with ctx.BLOCK(f'struct {struct_name}', trailing_semiconlon=True):
        for info in sorted(argsinfo, key=lambda ai: ai.name):   # sort by name
            cxx_type = value_type_to_cxx_type[info.value_type]
            yield f'// options: {info.options}, arg_type: {info.arg_type}'
            if info.default is None:
                if info.arg_type == ArgType.REST:
                    yield f'std::vector<{cxx_type}> {info.name};'
                else:
                    yield f'{cxx_type} {info.name};'
            else:
                assert info.arg_type != ArgType.REST
                default = info.default
                if info.value_type == ValueType.STRING:
                    default = repr_c_string(default)
                elif info.value_type == ValueType.BOOL:
                    default = 'true' if default else 'false'
                yield f'{cxx_type} {info.name} = {default};'

        yield ''
        yield 'std::string to_string() const;'
        yield f'bool operator==(const {struct_name} &rhs) const;'
        yield f'bool operator!=(const {struct_name} &rhs) const;'
        yield f'static {struct_name} parse_args(const std::vector<std::string> &args);'


def accecpt_rest_gen(ctx: Context, info: ArgInfo):
    if info.value_type == ValueType.STRING:
        yield f'ans.{info.name}.emplace_back(piece);'
    elif info.value_type == ValueType.INT:
        # FIXME: atol
        yield f'ans.{info.name}.emplace_back(atol(piece.data()))'
    else:
        assert False, 'unreachable'


def accept_arg_gen(ctx: Context, info: ArgInfo, source: str):
    if info.value_type == ValueType.STRING:
        yield f'ans.{info.name} = {source};'
    elif info.value_type == ValueType.INT:
        # FIXME: atol
        yield f'ans.{info.name} = atol({source});'
    else:
        assert False, 'unreachable'


def accept_arg_gen_with_default_check(ctx: Context, info: ArgInfo, source: str):
    yield from accept_arg_gen(ctx, info, source)
    if info.default is None:
        yield f'has_{info.name} = true;'


def use_next_arg_gen(ctx: Context, info: ArgInfo):
    yield 'i++;'
    with ctx.CONDITION():
        with ctx.IF("i == args.size() || args[i][0] == '-'"):
            yield 'throw ArgError("no value for " + piece);'
        with ctx.ELSE():
            yield from accept_arg_gen_with_default_check(ctx, info, 'args[i].data()')


def use_this_arg_gen(ctx: Context, info: ArgInfo, offset: str):
    yield from accept_arg_gen_with_default_check(ctx, info, f'piece.data() + {offset}')


def classify_options(options: Sequence[str]):
    short, long = [], []
    for opt in options:
        if opt.startswith('--'):
            long.append(opt)
        else:
            assert opt.startswith('-')
            short.append(opt)

    return short, long


def classify_to(options: Sequence[str], short_list: List[str], long_long: List[str]):
    short, long = classify_options(options)
    short_list.extend(short)
    long_long.extend(long)


def parse_args_method_gen(ctx: Context, struct_name: str, argsinfo: Sequence[ArgInfo]):
    option_to_arginfo = dict()  # type: Dict[str, ArgInfo]
    short_flags = []
    short_args = []
    short_count = []
    long_flags = []
    long_args = []
    long_count = []
    position_args = []
    rest_arg = None
    required_options = []

    for info in argsinfo:
        for opt in info.options:
            option_to_arginfo[opt] = info

        if info.arg_type == ArgType.BOOL:
            classify_to(info.options, short_flags, long_flags)
        elif info.arg_type == ArgType.COUNT:
            classify_to(info.options, short_count, long_count)
        elif info.arg_type == ArgType.ONE:
            if is_position_option(info.options):
                position_args.extend(info.options)
            else:
                classify_to(info.options, short_args, long_args)
                if info.default is None:
                    required_options.append(info.name)
        elif info.arg_type == ArgType.REST:
            assert rest_arg is None
            rest_arg = info
        else:
            assert False, 'unreachable'

    short_flags.sort()
    short_args.sort()
    short_count.sort()
    long_flags.sort()
    long_args.sort()
    long_count.sort()
    required_options.sort()

    with ctx.BLOCK(f'{struct_name} {struct_name}::parse_args(const std::vector<std::string> &args)'):
        yield f'{struct_name}' ' ans {};   // initialized'
        yield 'int position_count = 0;'
        yield '// required options'
        for opt in required_options:
            yield f'bool has_{opt} = false;'

        with ctx.BLOCK('for (size_t i = 0; i < args.size(); i++)'):
            yield 'const std::string &piece = args[i];'

            with ctx.CONDITION():
                # long options
                with ctx.IF("piece.size() > 2 && piece[0] == '-' && piece[1] == '-'"):
                    yield '// long options'
                    with ctx.CONDITION():
                        for opt in long_args:
                            info = option_to_arginfo[opt]
                            opt_str = repr_c_string(opt)
                            opt_eq_str = repr_c_string(opt + '=')
                            with ctx.MATCH(f'piece == {opt_str}'):
                                yield from use_next_arg_gen(ctx, info)
                            with ctx.MATCH(
                                f'piece.compare(0, strlen({opt_eq_str}), {opt_eq_str}) == 0'
                            ):
                                yield from use_this_arg_gen(ctx, info, f'strlen({opt_eq_str})')
                        for opt in long_flags:
                            info = option_to_arginfo[opt]
                            opt_str = repr_c_string(opt)
                            with ctx.MATCH(f'piece == {opt_str}'):
                                yield f'ans.{info.name} = true;'
                        for opt in long_count:
                            info = option_to_arginfo[opt]
                            opt_str = repr_c_string(opt)
                            with ctx.MATCH(f'piece == {opt_str}'):
                                yield f'ans.{info.name}++;'

                        with ctx.ELSE():
                            yield 'throw ArgError("Unknown option " + piece);'

                # short options
                with ctx.ELSEIF("piece.size() >= 2 && piece[0] == '-'"):
                    yield '// short options'
                    with ctx.CONDITION():
                        for opt in short_args:
                            opt_char = opt[1]
                            info = option_to_arginfo[opt]
                            with ctx.MATCH(f"piece[1] == '{opt_char}'"):
                                with ctx.CONDITION():
                                    with ctx.IF('piece.size() > 2'):
                                        yield from use_this_arg_gen(ctx, info, '2')
                                    with ctx.ELSE():
                                        yield from use_next_arg_gen(ctx, info)
                        with ctx.ELSE():
                            with ctx.BLOCK('for (auto it = piece.begin() + 1; it != piece.end(); ++it)'):
                                with ctx.CONDITION():
                                    for opt in short_flags:
                                        info = option_to_arginfo[opt]
                                        opt_char = opt[1]
                                        with ctx.MATCH(f"*it == '{opt_char}'"):
                                            yield f'ans.{info.name} = true;'
                                    for opt in short_count:
                                        info = option_to_arginfo[opt]
                                        opt_char = opt[1]
                                        with ctx.MATCH(f"*it == '{opt_char}'"):
                                                yield f'ans.{info.name}++;'

                                    with ctx.ELSE():
                                        yield 'throw ArgError("Unknown flag :" + *it);'

                # positional args
                with ctx.ELSE():
                    yield '// positional args'
                    with ctx.CONDITION():
                        for idx, opt in enumerate(position_args):
                            info = option_to_arginfo[opt]
                            with ctx.MATCH(f'position_count == {idx}'):
                                yield from accept_arg_gen(ctx, info, 'piece.data()')
                        with ctx.ELSE():
                            if rest_arg is not None:
                                yield from accecpt_rest_gen(ctx, rest_arg)
                            else:
                                yield 'throw ArgError("too many args: " + piece);'
                    yield 'position_count++;'

        yield ''
        yield '// check required options'
        for opt in required_options:
            with ctx.IF(f'!has_{opt}'):
                yield f'throw ArgError("{opt} required");'

        yield '// check positional args'
        position_count = len(position_args)
        with ctx.IF(f'position_count < {position_count}'):
            yield 'throw ArgError("expect more argument");'

        yield 'return ans;'


def to_string_method_gen(ctx: Context, struct_name: str, argsinfo: Sequence[ArgInfo]):
    # argsinfo = sorted(argsinfo, key=lambda ai: ai.name)     # sort by name

    with ctx.BLOCK(f'std::string {struct_name}::to_string() const'):
        yield f'std::string ans = "<{struct_name}";'

        for info in argsinfo:
            yield 'ans += %s;' % (repr_c_string(' ' + info.name + '='),)

            if info.arg_type == ArgType.REST:
                with ctx.BLOCK(f'for (const auto &item : this->{info.name})'):
                    if info.value_type == ValueType.STRING:
                        yield 'ans += item + ",";'
                    elif info.value_type == ValueType.INT:
                        yield 'ans += std::to_string(item) + ",";'
                    else:
                        assert False, 'unreachable'
            else:
                if info.value_type == ValueType.BOOL:
                    yield f'ans += this->{info.name} ? "true" : "false";'
                elif info.value_type == ValueType.INT:
                    yield f'ans += std::to_string(this->{info.name});'
                elif info.value_type == ValueType.STRING:
                    yield f'ans += \'"\' + this->{info.name} + \'"\';'
                else:
                    assert False, 'unreachable'

        yield 'return ans + ">";'


def prefix_list(prefix: str, arr: List):
    return [(prefix + x) for x in arr]


def comparison_method_gen(ctx: Context, struct_name: str, argsinfo: Sequence[ArgInfo]):
    names = sorted(info.name for info in argsinfo)
    lhs_tuple = ', '.join(prefix_list('this->', names))
    rhs_tuple = ', '.join(prefix_list('rhs.', names))

    with ctx.BLOCK(f'bool {struct_name}::operator==(const {struct_name} &rhs) const'):
        yield f'return std::tie({lhs_tuple}) \\'
        yield f'    == std::tie({rhs_tuple});'

    with ctx.BLOCK(f'bool {struct_name}::operator!=(const {struct_name} &rhs) const'):
        yield 'return !(*this == rhs);'


def warning_gen():
    yield '// WARNING: Automatically generated code by arggen.py. Do not edit.'


def header_gen(ctx: Context, struct_name: str, argsinfo: Sequence[ArgInfo], source_name: str):
    yield f'#ifndef ARGGEN_{source_name.upper()}_H'
    yield f'#define ARGGEN_{source_name.upper()}_H'
    yield ''
    yield from warning_gen()
    yield ''
    yield '#include <stdexcept>'
    yield '#include <string>'
    yield '#include <tuple>'
    yield '#include <vector>'
    yield from ('', '')

    with ctx.BLOCK('class ArgError : public std::runtime_error', trailing_semiconlon=True):
        yield Label('public:')
        yield 'ArgError(const std::string &msg) : std::runtime_error(msg) {}'
    yield from ('', '')

    yield from struct_gen(ctx, struct_name, argsinfo)
    yield ''

    yield f'#endif // ARGGEN_{source_name.upper()}_H'
    yield ''


def source_gen(ctx: Context, struct_name: str, argsinfo: Sequence[ArgInfo], source_name: str):
    yield '#include <cstring>'
    yield f'#include "{source_name}.h"'
    yield ''
    yield from warning_gen()
    yield from ('', '')

    yield from comparison_method_gen(ctx, struct_name, argsinfo)
    yield from ('', '')
    yield from to_string_method_gen(ctx, struct_name, argsinfo)
    yield from ('', '')
    yield from parse_args_method_gen(ctx, struct_name, argsinfo)
    yield ''
