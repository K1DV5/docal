# -ip
'''
various utility functions
'''
import ast
import re

# the tag pattern
PATTERN = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')


def _parens_balanced(expr: str) -> bool:
    '''
    check if the pairs that must be balanced are actually balanced
    '''
    # those that must be matched in equations
    parens = ['()', '[]', '{}']

    return all([expr.count(p[0]) == expr.count(p[1]) for p in parens])


def _split(what: str, char='=', count=None, last=True) -> list:
    '''split a given equation at the main equal signs and not at the ones
    used for other purposes like giving a kwarg'''

    balanced = []
    incomplete = ''
    for e in what.split(char):
        e = e.strip()
        if incomplete or not _parens_balanced(e):
            incomplete += (char if incomplete else '') + e
            if incomplete and _parens_balanced(incomplete):
                balanced.append(incomplete)
                incomplete = ''
        else:
            balanced.append(e)
    if incomplete:
        raise SyntaxError('The number of parens is not balanced.')
    if not count and len(balanced) > 1:
        if last:
            # if splitting only at the last = is wanted, join the others
            balanced = [char.join(balanced[:-1]), balanced[-1]]
        else:
            balanced = [balanced[0], char.join(balanced[1:])]

    return balanced


def _contin_type(accumul: str, line: str) -> bool:
    '''
    determine whether the line is part of a multi line part
    (for _split_module)
    '''
    if accumul and any([
        not _parens_balanced(accumul),
        accumul.rstrip()[-1] in ['\\', ':'],
        # or the line is indented and not a comment
        line and line[0].isspace() and not line.lstrip().startswith('#'),
        not line.strip()
    ]):
        return 'contin'
    elif (not _parens_balanced(line) or
            line.strip() and not line.lstrip().startswith(
                '#') and line.rstrip()[-1] in ['\\', ':']):
        return 'begin'


def _identify_part(part, comments):
    '''get the type of a string piece (assignment, expression, etc.)
    (for _split_module)
    '''

    part_ast = ast.parse(part).body
    if not part_ast:
        tag_match = PATTERN.match(part.strip())
        if tag_match and tag_match.group(0) == part.strip():
            return (part.strip()[1:], 'tag')
        elif part.lstrip().startswith('##'):
            if comments:
                return (part.lstrip()[2:], 'real-comment')
            else:
                return ('', 'comment')
        elif not part:
            return ('', 'comment')
        else:
            return (part.lstrip()[1:], 'comment')
    elif isinstance(part_ast[0], ast.Assign):
        return (part, 'assign')
    elif isinstance(part_ast[0], ast.Expr):
        return (part, 'expr')

    return (part, 'stmt')


def _split_module(module: str, char='\n', comments=False):
    '''
    split the given script string with the character/str using the rules
    '''
    returned = []
    # incomplete lines accululation, stored as [<accumululated>, <contin type>]
    accumul = ['', None]
    for part in module.split('\n'):
        contin_type = _contin_type(accumul[0], part)
        if contin_type:
            if contin_type == 'contin':
                accumul[0] += '\n' + part
            else:
                if accumul[0]:
                    returned.append(_identify_part(accumul[0], comments))
                accumul = [part, contin_type]
        else:
            if accumul[0]:
                returned.append(_identify_part(accumul[0], comments))
            returned.append(_identify_part(part, comments))
    if accumul[0]:
        returned.append(_identify_part(accumul[0], comments))

    return returned
