import xml.etree.ElementTree as ET
import re
from .excel import parse as parse_xl

dcl_pre_code = ['from math import *']

def parse(what):
    converted = []
    doc_tree = ET.fromstring(what)
    for child in doc_tree:
        if child.tag in ('ascii', 'python'):
            if child.tag == 'ascii':
                child.text = repl_asc(child.text)
            converted.append(child.text)
        elif child.tag == 'excel':
            converted.append(parse_xl(child.text))
    return '\n\n'.join(converted)

def repl_asc(lines: str):

    lines = lines.split('\n')
    # by value! not to repeat the last ones
    py_lines = dcl_pre_code[:]
    comment_pat = re.compile(r'^(?=[^#:].*?(\w+\s+?\w+)|(\\\w+).*?$)')
    for line in lines:
        # import statements and the like preceded with :
        line = comment_pat.sub('# ', line)
        py_lines.append(re.sub(r'^\:', '', line))
    py_legal = '\n'.join(py_lines)
    # change power symbol, not in comments
    py_legal = re.sub(r'(?sm)^([^\#].*?)\^', r'\1**', py_legal)
    # number coefficients like 2x
    py_legal = re.sub(r'(?<=[0-9])( ?[a-df-zA-Z_]|\()', '*\\1', py_legal)

    return py_legal


