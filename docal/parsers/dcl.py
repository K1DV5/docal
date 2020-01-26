from json import load
import re
from .excel import parse as parse_xl

dcl_pre_code = ['from math import *']

def parse(filename):
    with open(filename) as file:
        doc_tree = load(file)
    converted = []
    for child in doc_tree['data']:
        if child['type'] in ('ascii', 'python'):
            if child['type'] == 'ascii':
                # copy by value! not to repeat the last ones
                py_lines = dcl_pre_code[:] + \
                    [to_py(line) for line in child['data']]
                child['data'] = py_lines
            converted.append('\n'.join(child['data']))
        elif child['type'] == 'excel':
            converted.append(parse_xl(child['file'], child['sheet'], child['range']))
        else:
            print('dcl warning: unsupported type')
    return '\n\n'.join(converted)

def to_py(line):
    '''convert a single line to a form acceptable in python'''
    if not line.strip():
        return line
    if line.startswith(' ') or line.endswith(' '):  # text
        return '# ' + line.lstrip()
    elif line.startswith('$'):
        return '#' + line
    # change power symbol, not in comments
    line = line.replace('^', '**')
    # number coefficients like 2x
    line = re.sub(r'(?<=(?<!\w)[0-9])( ?[a-df-zA-Z_]|\()', '*\\1', line)
    return line
