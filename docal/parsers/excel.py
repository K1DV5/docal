EXCEL_SEP = '|'
# for excel file handling
NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'x14ac': 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac',
}

class ExcelCalc:

    xl_cell_pat = re.compile(r'[A-Z]+[0-9]+')
    xl_func_pat = re.compile(r'[A-Z]+(?=\()')
    xl_params = ['file', 'sheet', 'range']

    def repl_xl(self, lines: str):
        lines = lines.strip().split('\n')
        params = {
                'file': '',
                'sheet': 1,
                'range': None,
                }
        for param in [line.split(EXCEL_SEP)[:2] for line in lines]:
            try:
                key, val = param
            except ValueError:
                raise SyntaxError('Invalid syntax, must be in the form [parameter]' + EXCEL_SEP + ' [value]')
            else:
                if key.strip() in self.xl_params:
                    params[key.strip()] = val.strip()
        return self.xl_convert(file=params['file'],
                               sheet=params['sheet'],
                               range=params['range'])

    def xl_convert(self, file='', sheet=1, range=None):

        with ZipFile(file, 'r') as zin:
            sheet_xml = zin.read(f'xl/worksheets/sheet{int(sheet)}.xml').decode('utf-8')
            str_xml = zin.read('xl/sharedStrings.xml').decode('utf-8')

        sheet_tree = ET.fromstring(sheet_xml)
        str_tree = ET.fromstring(str_xml)
        rows = sheet_tree.find('{%s}sheetData' % NS['main'])
        self.temp_var['strs'] = [node[0].text for node in str_tree]
        range = self.xl_find_range(rows, self.temp_var['strs'], range)
        self.temp_var['info'] = self.xl_extract_info(rows, range)

        return self.xl_info_2_script(self.temp_var['info'])

    def xl_info_2_script(self, info):
        tag = self.current_tag
        script = []
        for key, content in info.items():
            if content[0][0] == 'txt':
                para = content[0][1]
                if para.lstrip().startswith('#'):
                    # means its a tag
                    tag = self.current_tag = part[0]
                    logger.info('[Change tag] #%s', tag)
                else:
                    for part in self._process_comment(para):
                        script.append((tag, part))
            elif content[0][0] == 'var':
                var_name = content[0][1]
                if len(content[1]) == 2:
                    steps = [content[1][1]]
                else:
                    steps = [self.xl_form2expr(0, 1, content), self.xl_form2expr(1, -1, content)]
                steps.append(content[1][-1])
                opt = content[-1][-1].replace('^', '**') if content[-1][0] == 'opt' else ''
                try:  # check if the var name is python legal
                    to_math(var_name + '=' + steps[-1])
                except SyntaxError:
                    eqn_xl = cal([f'"{var_name}"', steps, opt], working_dict=self.working_dict, typ=self.doc_type)
                else:
                    eqn_xl = cal([var_name, steps, opt], working_dict=self.working_dict, typ=self.doc_type)
                script.append((tag, (eqn_xl[1], eqn_xl[0])))

        return script

    def xl_find_range(self, rows, strs, given_range):
        '''convert a given range to a more useful one:
        (the letter, the starting index in tree, the row number of last)'''

        if given_range:
            if type(given_range) == str:
                # must be in the form "A, 1-10"
                col_let, n_range = [r.strip() for r in given_range.split(',')]
                r_start, r_end = [int(r) for r in n_range.split('-')]
                given_range = (col_let, r_start, r_end)
            for i_row, row in enumerate(rows):
                if int(row.attrib['r']) == given_range[1]:
                    xlrange = (given_range[0], i_row, given_range[2])
        else:
            found = False
            for i_row, row in enumerate(rows):
                for cell in row:
                    if 't' in cell.attrib and cell.attrib['t'] == 's' \
                            and strs[int(cell[0].text)]:
                        col_let = ''.join(
                            [c for c in cell.attrib['r'] if c.isalpha()])
                        xlrange = (col_let, i_row, int(rows[-1].attrib['r']))
                        found = True
                        break
                if found:
                    break

        return xlrange

    def xl_process_cell(self, cell, line, current_col, current_key):
        cont = ['txt', '']
        if 't' in cell.attrib and cell.attrib['t'] == 's':
            cont = ['txt', self.temp_var['strs'][int(cell[0].text.strip())]]
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

    def xl_extract_info(self, rows, range):

        # store calcs in dict with cell addreses as keys
        info = {}

        for i_row, row in enumerate(rows[range[1]:]):
            if int(row.attrib['r']) <= range[2]:
                line = []
                # default key unless changed (below)
                current_key = f'para{i_row}'
                current_col = -1
                for cell in row:
                    col_let = ''.join(
                        [c for c in cell.attrib['r'] if c.isalpha()])
                    if col_let == range[0]:
                        current_col = 0
                    if current_col in [0, 1, 2]:
                        line, current_col, current_key = \
                                self.xl_process_cell(cell, line, current_col, current_key)
                info[current_key] = line
        return info
    
    def xl_form2expr(self, ins1, ins2, content):
        try:
            correct = self.xl_cell_pat.sub(
                lambda x: self.temp_var['info'][x.group(0)][ins1][ins2],
                content[1][1]).replace('^', '**')
        except KeyError as err:
            raise ReferenceError(f'Cell reference \'{err.args[0]}\' outside of scanned range')
        correct = self.xl_func_pat.sub(lambda x: x.group(0).lower(), correct)
        return correct.replace('^', '**')

