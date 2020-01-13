import xml.etree.ElementTree as ET
import re
from zipfile import ZipFile

import logging

logger = logging.getLogger(__name__)

NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'x14ac': 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac',
}

xl_cell_pat = re.compile(r'[A-Z]+[0-9]+')
xl_func_pat = re.compile(r'[A-Z]+(?=\()')

def parse(file='', sheet=1, range=None):

    with ZipFile(file, 'r') as zin:
        sheet_xml = zin.read(f'xl/worksheets/sheet{sheet}.xml').decode('utf-8')
        str_xml = zin.read('xl/sharedStrings.xml').decode('utf-8')

    # shared strings
    str_tree = ET.fromstring(str_xml)
    strings = [node[0].text for node in str_tree]
    # desired region
    sheet_tree = ET.fromstring(sheet_xml)
    rows = sheet_tree.find('{%s}sheetData' % NS['main'])
    range = find_range(rows, strings, range)
    info = extract_info(rows, strings, range)

    return info_2_script(info)


def find_range(rows, strs, given_range):
    '''convert a given range to a more useful one:
    (the letter, the starting index in tree, the row number of last)'''

    if given_range:
        if type(given_range) == str:
            # must be in the form "A, 1-10"
            col_let, n_range = [r.strip() for r in given_range.split(',')]
            r_start, r_end = [r for r in n_range.split('-')]
            given_range = (col_let, r_start, r_end)
            if not col_let or not r_start:
                raise ValueError('Range needs to be in the form eg: A,10-23')
            r_start = int(r_start)
            if not r_end:
                raise NotImplementedError('Incomplete range not implemented yet')
            r_end = int(r_end)
        for i_row, row in enumerate(rows):
            if int(row.attrib['r']) == given_range[1]:
                return (given_range[0], i_row, given_range[2])
    for i_row, row in enumerate(rows):
        for cell in row:
            if 't' in cell.attrib and cell.attrib['t'] == 's' \
                    and strs[int(cell[0].text)]:
                col_let = ''.join(
                    [c for c in cell.attrib['r'] if c.isalpha()])
                return (col_let, i_row, int(rows[-1].attrib['r']))
    return False

def info_2_script(info):
    script = []
    for key, content in info.items():
        if content[0][0] == 'txt':
            # text or para
            para = content[0][1]
            if para.startswith('#'):  #tag
                script.append(para)
            elif para.strip():  #text
                script.append('# ' + para)
            else:  #empty line
                script.append('')
        elif content[0][0] == 'var':
            options = content[-1][-1].replace('^', '**') if content[-1][0] == 'opt' else ''
            assignment = content[0][1] + '='
            if len(content[1]) == 2:  # no formula, just a value
                assignment += content[1][1]
            else:
                assignment += form2expr(0, 1, content, info)
                options = '=' + form2expr(1, -1, content, info) + ',' + options
            script.append(assignment + ' #' + options.strip(','))

    return '\n'.join(script)

def process_cell(cell, line, strings, current_col, current_key):
    cont = ['txt', '']
    if 't' in cell.attrib and cell.attrib['t'] == 's':
        cont = ['txt', strings[int(cell[0].text.strip())]]
    elif cell.findall('{%s}f' % NS['main']):
        cont = ['expr', cell[0].text, cell[1].text]
    elif len(cell):
        cont = ['val', cell[0].text]

    if current_col == 0:
        line.append(cont)
        current_col += 1
    elif current_col == 1:
        if line[0][0] == 'txt' and cont[1].strip():
            line[0][0] = 'var'
            line[0][1] = f'{line[0][1]}'
            if cont[0] == 'txt':
                cont[1] = f'"{cont[1]}"'
            line.append(cont)
            current_key = cell.attrib['r']
            current_col += 1
    else:
        if line[0][0] == 'var':
            if cont[0] == 'txt':
                line.append(['opt', cont[1]])
                current_col += 1

    return line, current_col, current_key

def extract_info(rows, strings, range_xl):

    # store calcs in dict with cell addreses as keys
    info = {}

    last_row = range_xl[1] - 1  # for empty lines
    for row in rows[range_xl[1]:]:
        i_row = int(row.attrib['r'])
        # empty lines (rows)
        for i_empty in range(last_row + 1, i_row):
            info[f'para{i_empty}'] = [['txt', '']]
        last_row = i_row
        # default key unless changed (below)
        current_key = f'para{i_row}'
        current_col = -1
        line = []
        for cell in row:
            col_let = ''.join(
                [c for c in cell.attrib['r'] if c.isalpha()])
            if col_let == range_xl[0]:
                current_col = 0
            if current_col in [0, 1, 2]:
                line, current_col, current_key = \
                        process_cell(cell, line, strings, current_col, current_key)
        info[current_key] = line
        if int(row.attrib['r']) == range_xl[2]: break
    return info

def form2expr(ins1, ins2, content, info):
    try:
        correct = xl_cell_pat.sub(
            lambda x: info[x.group(0)][ins1][ins2],
            content[1][1]).replace('^', '**')
    except KeyError as err:
        raise ReferenceError(f'Cell reference \'{err.args[0]}\' outside of scanned range')
    correct = xl_func_pat.sub(lambda x: x.group(0).lower(), correct)
    return correct.replace('^', '**')

# print(parse('../../tests/test/e.xlsx'))
