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


def _to_incomplete(incomplete: str, line: str) -> bool:
    '''
    determine whether the line should be sent to the incomplete storage or not
    '''
    conditions = [
        # if there is an incomplete part, and it doesn't have equal parens,
        incomplete and not any([_parens_balanced(incomplete),
                                # or ends with \ or :
                                incomplete.rstrip().endswith('\\'),
                                incomplete.rstrip().endswith(':')]),
        # or the line is indented and not a comment
        line and line[0].isspace() and not line.lstrip().startswith('#'),
        # or the line is not a comment and is a beginning of a block
        # or the parens are not balanced
        all([line, not line.lstrip().startswith('#'),
             line.rstrip().endswith(':') or not _parens_balanced(line)]),
        # or the line is blank and there is an incomplete part
        not line.strip() and incomplete
    ]

    return any(conditions)


def _split_module(module: str, char='\n'):
    '''
    split the given script string with the character/str using the rules
    '''
    returned = []
    incomplete = ''
    for part in module.split('\n'):
        # this will accumulate the lines. If the intent is an assignment, the
        # last line has to be added to make it up. If the intent is execution,
        # the accumulated can be executed directly and the last line has to be
        # considered from the beginning.
        if _to_incomplete(incomplete, part):
            incomplete += part + char
            part = None
        if part is not None:
            if incomplete:
                inc_type = ast.parse(incomplete).body
                if inc_type and isinstance(inc_type[0], ast.Assign):
                    returned.append((incomplete, 'assign'))
                else:
                    returned.append((incomplete, 'stmt'))
                incomplete = ''
            part_ast = ast.parse(part).body
            if not part_ast:
                tag_match = PATTERN.match(part.strip())
                if tag_match and tag_match.group(0) == part.strip():
                    returned.append((part.strip()[1:], 'tag'))
                elif part.lstrip().startswith('##') or not part:
                    returned.append(('', 'comment'))
                else:
                    returned.append((part.lstrip()[1:], 'comment'))
            elif isinstance(part_ast[0], ast.Assign):
                returned.append((part, 'assign'))
            else:
                returned.append((part, 'stmt'))
    if incomplete:
        inc_type = ast.parse(incomplete).body
        if inc_type and isinstance(inc_type[0], ast.Assign):
            returned.append((incomplete, 'assign'))
        else:
            returned.append((incomplete, 'stmt'))
        incomplete = ''
    return returned
