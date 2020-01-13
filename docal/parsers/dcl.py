from json import load
import re
from .excel import parse as parse_xl

dcl_pre_code = ['from math import *']

def parse(filename):
    with open(filename) as file:
        doc_tree = load(file)
    converted = []
    for child in doc_tree['content']:
        if child['type'] in ('ascii', 'python'):
            if child['type'] == 'ascii':
                # copy by value! not to repeat the last ones
                py_lines = dcl_pre_code[:] + \
                    [to_py(line) for line in child['content'].split('\n')]
                child['content'] = '\n\n'.join(py_lines)
            converted.append(child['content'])
        elif child['type'] == 'excel':
            converted.append(parse_xl(child['file'], child['sheet'], child['range']))
        else:
            print('dcl warning: unsupported type')
    return '\n\n'.join(converted)

def to_py(line):
    '''convert a single line to a form acceptable in python'''
    if not line.strip():
        return line
    # import statements and the like preceded with :
    if line.startswith(':'):
        return line[1:]
    is_text = re.search(r'(\w+ +\w+)|(\\\w+)', line) or line.startswith(' ') or line.endswith(' ')
    if is_text and not line.startswith('#'):
        return '# ' + line.lstrip()
    elif line.startswith('$'):
        return '#' + line
    # change power symbol, not in comments
    line = line.replace('^', '**')
    # number coefficients like 2x
    line = re.sub(r'(?<=[0-9])( ?[a-df-zA-Z_]|\()', '*\\1', line)
    return line
