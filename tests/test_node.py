from arggen import Root, Block, Condition, If, ElseIf, Else, Context, collect_node


def test_block():
    block = Block('head')
    block.add_child('asdf')
    block.add_child('1234')

    assert '\n'.join(block.to_source(0)) == '''
head {
    asdf
    1234
}'''[1:]


def test_if():
    ifthen = If('abc')
    ifthen.add_child('asdf')

    assert '\n'.join(ifthen.to_source(0)) == '''
if (abc) {
    asdf
}'''[1:]


def test_condition():
    cond = Condition()
    ifthen = If('a').add_child('aaa')
    elseif = ElseIf('b').add_child('bbb')
    cond.add_child(ifthen).add_child(elseif)

    assert '\n'.join(cond.to_source(0)) == '''
if (a) {
    aaa
} else if (b) {
    bbb
}'''[1:]

    elsethen = Else().add_child('ccc')
    cond.add_child(elsethen)
    assert '\n'.join(cond.to_source(0)) == '''
if (a) {
    aaa
} else if (b) {
    bbb
} else {
    ccc
}'''[1:]


def test_condition_dangling_else():
    cond = Condition().add_child(
        Else().add_child('asdf'))
    assert '\n'.join(cond.to_source(0)) == 'asdf'


def test_nested():
    block = Block('head')\
        .add_child('123')\
        .add_child('asdf')\
        .add_child(Condition()
            .add_child(If('a')
                .add_child('aaa'))
            .add_child(ElseIf('b')
                .add_child(Block('bbb')
                    .add_child('BBB'))))

    assert '\n'.join(block.to_source(0)) == '''
head {
    123
    asdf
    if (a) {
        aaa
    } else if (b) {
        bbb {
            BBB
        }
    }
}'''[1:]


def test_collect_node():
    def g(ctx: Context):
        with ctx.BLOCK('head'):
            yield 'abc'
            with ctx.IF('a'):
                yield 'AAA'
            with ctx.CONDITION():
                with ctx.IF('b'):
                    yield 'BBB'
                with ctx.ELSE():
                    yield 'CCC'
            yield 'zzz'

    assert collect_node(g) == \
        Root().add_child(Block('head')\
            .add_child('abc')\
            .add_child(If('a').add_child('AAA'))\
            .add_child(Condition()
                .add_child(If('b').add_child('BBB'))
                .add_child(Else().add_child('CCC')))\
            .add_child('zzz'))
