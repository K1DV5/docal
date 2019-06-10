# Written by K1DV5
'''
Module document

provides the document class that can be used to
replace the pythontex and pweave requirement.

In the latex file,
    use hashtags(#tagname) to reserve places for contents that
    will come from the python script.
In a separate python script,
    import this class.
    use methods tag('tagname') for something like tags(placeholders)
    write your calculations under those tags using ins(contents) to choose
        what goes to the document tag place.
    Finally use the write() method to write the final file.

when the python file is run, it writes a tex file with the tags
replaced by contents from the python file.
'''

# for tag replacements
import re
# to know types of strings (assignment or module)
import ast
# to run pandoc
from subprocess import run
# for path manips
from os import path
# for word file handling
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
# for temp directory
import tempfile
# for status tracking
import logging
from shutil import move, rmtree
# for working with the document's variables and filename
try:
    from __main__ import __dict__ as DICT
except ImportError:
    DICT = {}
from .calculation import cal
from .parsing import UNIT_PF, eqn, latexify
# to split the calculation string
from .utils import _split_module
DEFAULT_FILE = 'Untitled.tex'
# the tag pattern
PATTERN = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')
# surrounding of the content sent for reversing (something that doesn't
# change the actual content of the document, and works inside lines)
SURROUNDING = ['{} {{ {}', '{} }} {}']

LOG_FORMAT = '%(levelname)s: %(message)s'
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class latexFile:
    '''handles the latex files'''

    # warning for tag place protection in document:
    warning = ('BELOW IS AN AUTO GENERATED LIST OF TAGS. '
               'DO NOT DELETE IT IF REVERSING IS DESIRED!!!\n%')

    def __init__(self, infile, to_clear):

        self.to_clear = to_clear
        if infile:
            self.infile = self.outfile = infile
            with open(self.infile) as file:
                self.file_contents = file.read()
            # the collection of tags at the bottom of the file for reversing
            self.tagline = re.search(fr'\n% *{re.escape(self.warning)}'
                                     r'*[\[[a-zA-Z0-9_ ]+\]\]',
                                     self.file_contents)
            # remove previous calculation parts
            if self.tagline:
                start = self.tagline.group(0).find('[[') + 2
                end = self.tagline.group(0).rfind(']]')
                self.tags = self.tagline.group(0)[start:end].split()
                self._revert_tags()
            self.tags = [tag.group(2)
                         for tag in PATTERN.finditer(self.file_contents)]
        else:
            self.file_contents = self.infile = self.tagline = self.tags = None
            self.outfile = DEFAULT_FILE
        self.calc_tags = []

    def _revert_tags(self):
        # remove the tagline
        file_str = (self.file_contents[:self.tagline.start()].rstrip() +
                    self.file_contents[self.tagline.end():])
        # replace the sent regions with their respective tags
        for tag in self.tags:
            file_str = re.sub(r'(?s)'
                              + re.escape(SURROUNDING[0])
                              + '.*?'
                              + re.escape(SURROUNDING[1]),
                              '#' + tag, file_str, 1)
        # for inplace editing
        self.file_contents = file_str
        return file_str

    def _subs_in_place(self, values: dict):
        file_str = self.file_contents + f'\n\n% {self.warning} [['
        file_str = PATTERN.sub(lambda x: self._repl(x, True, values),
                               file_str)
        for tag in self.calc_tags:
            file_str += tag + ' '
        file_str = file_str.rstrip('\n') + ']]'
        return file_str

    def _subs_separate(self, values: dict):
        return PATTERN.sub(lambda x: self._repl(x, False, values),
                           self.file_contents)

    def _repl(self, match_object, surround: bool, values: dict):
        start, tag, end = [m if m else '' for m in match_object.groups()]
        if tag in values:
            result = '\n'.join(values[tag])
            if surround:
                return (start
                        + SURROUNDING[0]
                        + (start if start == '\n' else '')
                        + result
                        + (end if end == '\n' else '')
                        + SURROUNDING[1]
                        + end)

            return start + result + end
        logger.error(f"There is nothing to send to #{tag}.")
        return start + '#' + tag + end

    def write(self, outfile=None, values={}):
        if outfile:
            self.outfile = outfile

        if not self.to_clear:
            if self.infile:
                for tag in values:
                    if tag in self.tags:
                        self.calc_tags.append(tag)
                    else:
                        logger.error(f'#{tag} not found in the document.')
                if path.abspath(self.outfile) == path.abspath(self.infile):
                    self.file_contents = self._subs_in_place(values)
                else:
                    self.file_contents = self._subs_separate(values)
            else:
                self.file_contents = '\n'.join([
                    '\n'.join(val) for val in values.values()
                ])

        logger.info('[writing file] %s', self.outfile)
        with open(self.outfile, 'w') as file:
            file.write(self.file_contents)


class wordFile:

    # the xml declaration
    declaration = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
    # always required namespaces
    namespaces = {
        "wpc": "http://schemas.microsoft.com/office/word/2010/wordprocessingcanvas",
        "cx": "http://schemas.microsoft.com/office/drawing/2014/chartex",
        "cx1": "http://schemas.microsoft.com/office/drawing/2015/9/8/chartex",
        "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
        "o": "urn:schemas-microsoft-com:office:office",
        "r": "http://schemas.openxmlformats.org/officedocument/2006/relationships",
        "m": "http://schemas.openxmlformats.org/officedocument/2006/math",
        "v": "urn:schemas-microsoft-com:vml",
        "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingdrawing",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingdrawing",
        "w10": "urn:schemas-microsoft-com:office:word",
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
        "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
        "w16se": "http://schemas.microsoft.com/office/word/2015/wordml/symex",
        "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessinggroup",
        "wpi": "http://schemas.microsoft.com/office/word/2010/wordprocessingink",
        "wne": "http://schemas.microsoft.com/office/word/2006/wordml",
        "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingshape",
    }

    # the internal form of the parsed tags for internal use to avoid normal # usage
    tag_alt_form = '#{%s}'

    def __init__(self, infile, to_clear=False):
        # temp folder for converted files
        self.temp_dir = tempfile.mkdtemp()
        # file taken as input file when not explicitly set:
        if infile:
            self.infile = infile
            base, ext = path.splitext(self.infile)
            self.outfile = base + '-out' + ext
            with ZipFile(infile, 'r') as zin:
                file_contents = zin.read('word/document.xml')
                self.tmp_file = ZipFile(path.join(
                    self.temp_dir, path.splitext(path.basename(self.infile))[0]),
                    'w', compression=ZIP_DEFLATED)
                self.tmp_file.comment = zin.comment
                for file in zin.namelist():
                    if file != 'word/document.xml':
                        self.tmp_file.writestr(file, zin.read(file))

            # the xml tree representation of the document contents
            self.doc_tree = ET.fromstring(file_contents)
            for prefix, uri in self.namespaces.items():
                ET.register_namespace(prefix, uri)

            # the tags in the document (stores tags, their addresses, and whether inline)
            self.tags_info = self.extract_tags_info(self.doc_tree)
            self.tags = [info['tag'] for info in self.tags_info]
        else:
            self.tmp_file = path.join(
                self.temp_dir, path.splitext(
                    path.basename(DEFAULT_FILE))[0])
            self.infile = self.doc_tree = self.tags_info = self.tags = None
            self.outfile = DEFAULT_FILE.replace('.tex', '.docx')

    def normalized_contents(self, paragraph):
        pref_w = f'{{{self.namespaces["w"]}}}'
        ignored = [pref_w + tag for tag in ['bookmarkStart', 'bookmarkEnd']]
        conts = []
        for r in paragraph:
            if r.tag == pref_w + 'r':
                if conts:
                    if type(conts[-1]) == list:
                        conts[-1].append(r)
                    else:
                        conts.append(['', r])
                else:
                    conts.append(['', r])
                for t in r:
                    if t.tag == pref_w + 't':
                        conts[-1][0] += t.text
            elif r.tag not in ignored:
                conts.append(r)
        return conts

    def extract_tags_info(self, tree):

        pref_w = f'{{{self.namespaces["w"]}}}'
        tags_info = []
        for index, child in enumerate(tree[0]):
            if child.tag == pref_w + 'p':
                # get its contents and clear it
                conts = self.normalized_contents(child)
                child.clear()
                for cont in conts:
                    if type(cont) == list:
                        if '#' in cont[0]:
                            # replace with a new element
                            w_r = ET.SubElement(child, pref_w + 'r')
                            w_t = ET.SubElement(w_r, pref_w + 't',
                                                {'xml:space': 'preserve'})
                            # store full info about the tags inside
                            for tag in PATTERN.finditer(cont[0]):
                                if cont[0].strip() == '#' + tag.group(2):
                                    position = 'para'
                                else:
                                    position = 'inline'
                                tags_info.append({
                                    'tag': tag.group(2),
                                    'tag-alt': self.tag_alt_form % tag.group(2),
                                    'address': [child, w_r, w_t],
                                    'position': position,
                                    'index': index})
                            # remove \'s from the escaped #'s and change the tags form
                            w_t.text = (re.sub(r'\\#', '#', PATTERN.sub(
                                lambda tag:
                                    tag.group(1) +
                                    self.tag_alt_form % tag.group(2) +
                                    tag.group(3),
                                cont[0])))
                        else:  # preserve properties
                            for r in cont[1:]:
                                child.append(r)
                    else:
                        child.append(cont)

        return tags_info

    def _subs_tags(self, values={}):
        ans_tree = self._get_ans_tree(values)
        ans_tag_info = self.extract_tags_info(ans_tree)

        indices = [info['index'] for info in ans_tag_info]
        ans_len = len(ans_tree[0])
        # add one to skip the tags
        ranges = list(zip([i + 1 for i in indices], indices[1:] + [ans_len]))
        # get ans elements in (tag, (start, end)) form
        ans_info = [(info['tag'], ranges[i])
                    for i, info in enumerate(ans_tag_info)]

        added = 0  # the added index to make up for the added elements
        for tag, (start, end) in ans_info:
            matching_infos = [
                info for info in self.tags_info if info['tag'] == tag]
            if matching_infos:
                info = matching_infos[0]
                # remove this entry to revert the left ones from their alt form
                self.tags_info.remove(info)
                ans_parts = ans_tree[0][start: end]
                if info['position'] == 'para':
                    ans_parts.reverse()  # because they are inserted at the same index
                    for ans in ans_parts:
                        self.doc_tree[0].insert(info['index'] + added, ans)
                    self.doc_tree[0].remove(info['address'][0])
                    added += len(ans_parts) - 1  # minus the tag para (removed)
                else:
                    loc_para, loc_run, loc_text = info['address']
                    split_text = loc_text.text.split(info['tag-alt'], 1)
                    loc_text.text = split_text[1]
                    index_run = list(loc_para).index(loc_run)
                    pref_w = f'{{{self.namespaces["w"]}}}'
                    # if there is only one para, insert its contents into the para
                    if len(ans_parts) == 1:
                        ans_runs = list(ans_parts[0])
                        ans_runs.reverse()  # same reason as above
                        for run in ans_runs:
                            loc_para.insert(index_run, run)
                        beg_run = ET.Element(pref_w + 'r')
                        beg_text = ET.SubElement(beg_run, pref_w + 't',
                                                 {'xml:space': 'preserve'})
                        beg_text.text = split_text[0]
                        loc_para.insert(index_run, beg_run)
                    else:  # split the para and make new paras between the splits
                        beg_para = ET.Element(pref_w + 'p')
                        beg_run = ET.SubElement(beg_para, pref_w + 'r')
                        beg_text = ET.SubElement(beg_run, pref_w + 't',
                                                 {'xml:space': 'preserve'})
                        beg_text.text = split_text[0]
                        ans_parts.reverse()  # same reason as above
                        for ans in ans_parts:
                            self.doc_tree[0].insert(info['index'] + added, ans)
                        beg_index = info['index'] + added
                        self.doc_tree[0].insert(beg_index, beg_para)
                        added += len(ans_parts) + 1
            else:
                logger.error(f'#{tag} not found in the document.')
        # revert the rest of the tags from their alt form
        for info in self.tags_info:
            logger.error(f'There is nothing to send to #{info["tag"]}.')
            loc_text = info['address'][2]
            loc_text.text = loc_text.text.replace(
                info['tag-alt'], '#' + info['tag'])

    def _get_ans_tree(self, values={}):
        result_str = '\n\n'.join(['#' +
                                  tag.replace('_', '\\_') +
                                  '\n\n' +
                                  '\n'.join(value)
                                  for tag, value in values.items()])
        result_tex = path.join(
            self.temp_dir, path.basename(self.infile) + '-res.tex')
        result_docx = path.splitext(result_tex)[0] + '.docx'
        with open(result_tex, 'w') as file:
            file.write(result_str)
        run(['pandoc', result_tex, '-o', result_docx])
        with ZipFile(result_docx) as docx:
            ans_tree = ET.fromstring(docx.read('word/document.xml'))

        return ans_tree

    def write(self, outfile=None, values={}):
        if outfile:
            self.outfile = outfile

        if self.infile:
            self._subs_tags(values)
            # take care of namespaces and declaration
            doc_xml = ET.tostring(self.doc_tree, encoding='unicode')
            searched = re.match(r'\<w:document.*?\>', doc_xml).group(0)
            used_nses = re.findall(r'(?<=xmlns\:)\w+', searched)
            for prefix, uri in self.namespaces.items():
                if prefix not in used_nses:
                    self.doc_tree.set('xmlns:' + prefix, uri)

            doc_xml = self.declaration + \
                ET.tostring(self.doc_tree, encoding='unicode')
            self.tmp_file.writestr('word/document.xml', doc_xml)
            tmp_fname = self.tmp_file.filename
            self.tmp_file.close()
        else:
            with open(self.tmp_file, 'w') as file:
                file.write('\n'.join([
                    '\n'.join(val) for val in values.values()
                ]))
            tmp_fname = path.splitext(self.tmp_file)[0] + '.docx'
            run(['pandoc', self.tmp_file, '-f', 'latex', '-o', tmp_fname])

        logger.info('[writing file] %s', self.outfile)
        move(tmp_fname, self.outfile)

        rmtree(self.temp_dir)


class LogRecorder(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log = []

    def emit(self, record):
        self.log.append(self.format(record))


class document:
    '''organize the process by taking tags from the filetype-specific classes,
    making a dictionary for them, and calling the write method of those classes
    giving them the dictionary'''

    file_handlers = {
        '.docx': wordFile,
        '.tex': latexFile,
    }

    def __init__(self, infile=None, to_clear=False, log_level=None, log_file=False):
        '''initialize'''

        self.to_clear = to_clear
        # clear previous handlers so the logs are only for the current run
        log_formatter = logging.Formatter(LOG_FORMAT)
        # log messages
        self.log = []
        self.log_recorder = LogRecorder()
        self.log_recorder.setFormatter(log_formatter)
        # to avoid repeatedly adding the same handler
        logger.handlers = []
        logger.addHandler(self.log_recorder)
        if log_level:
            logger.setLevel(getattr(logging, log_level.upper()))
        # the document
        if infile:
            infile = path.abspath(infile)
            basename, ext = path.splitext(infile)
            self.document_file = self.file_handlers[ext](infile, to_clear)
            self.tags = self.document_file.tags
            if log_file:
                file_logger = logging.FileHandler(basename + '.log', 'w')
                file_logger.setFormatter(logging.Formatter(LOG_FORMAT))
                logger.addHandler(file_logger)
        else:
            self.document_file = None
            self.tags = []
        if log_level:
            logger.setLevel(getattr(logging, log_level.upper()))
        # the calculations corresponding to the tags
        self.contents = {}
        self.current_tag = self.tags[0] if self.tags else None
        if self.current_tag is None:
            logger.error('There are no tags in the document')
        # temp storage for assignment statements where there are unmatched parens
        self.incomplete_assign = ''
        # temp storage for block statements like if and for
        self.incomplete_stmt = ''

    def _format_value(self, var, working_dict=DICT):
        if var in working_dict:
            unit_name = var + UNIT_PF
            unit = fr' \, \mathrm{{{latexify(working_dict[unit_name], div_symbol="/", working_dict=working_dict)}}}'\
                if unit_name in working_dict.keys() and working_dict[unit_name] \
                and working_dict[unit_name] != '_' else ''
            result = eqn(latexify(
                working_dict[var]) + unit, norm=False, disp=False)
        else:
            raise KeyError(f"'{var}' is an undefined variable.")

        return result

    def _process_comment(self, line, working_dict=DICT):
        '''
        convert comments to latex paragraphs
        '''

        logger.info('[Processing] %s', line)
        if line.startswith('$'):
            line = re.sub(r'(?a)#(\w+)',
                          lambda x: 'TMP0'.join(
                              x.group(1).split('_')) + 'TMP0',
                          line)
            if line.startswith('$$'):
                line = eqn(line[2:])
            elif line.startswith('$where'):
                # usually after equations
                defns = [defn.split('=')
                                    for defn in line.split(' ', 1)[1].split(',')]
                defns = eqn(
                    '|'.join([var + ' = "' + mean + '"' for var, mean in defns]))
                line = '\nwhere\n' + defns
            else:
                line = eqn(line[1:], disp=False)
            augmented = re.sub(r'(?a)\\mathrm\s*\{\s*(\w+)TMP0\s*\}',
                               lambda x: latexify(
                                   working_dict['_'.join(x.group(1).split('TMP0'))]),
                               line)
        else:
            augmented = PATTERN.sub(lambda x: x.group(1) +
                                    self._format_value(x.group(2)) +
                                    x.group(3), line.lstrip())

        return augmented

    def _process_assignment(self, line, working_dict=DICT):
        '''
        evaluate assignments and convert to latex form
        '''
        logger.info('[Processing] %s', line)
        # the cal function will execute it so no need for exec
        return cal(line, working_dict)

    def process_content(self, input_str, working_dict=DICT):
        tag = self.current_tag
        processed = []
        for part in _split_module(input_str):
            if part[1] == 'tag':
                tag = part[0]
                logger.info('[Change tag] #%s', tag)
            elif part[1] in ['assign', 'expr']:
                processed.append(
                    (tag, self._process_assignment(part[0], working_dict)))
            elif part[1] == 'comment':
                processed.append(
                    (tag, self._process_comment(part[0], working_dict)))
            elif part[1] == 'stmt':
                # if it does not appear like an equation or a comment,
                # just execute it
                logger.info('[Executing] %s', part[0])
                exec(part[0], working_dict)
                if part[0].startswith('del '):
                    # also delete associated unit strings
                    variables = [v.strip()
                                 for v in part[0][len('del '):].split(',')]
                    for v in variables:
                        if v + UNIT_PF in working_dict:
                            del working_dict[v + UNIT_PF]
        return processed

    def send(self, content):
        '''add the content to the tag, which will be sent to the document.
        Where it will be inserted is decided by the most recent tag.'''

        if not self.to_clear:
            tag = self.current_tag
            logger.info('[Change tag] #%s', tag)
            for tag, part in self.process_content(content):
                if tag == '_':
                    tag = self.current_tag
                if tag not in self.contents.keys():
                    self.contents[tag] = []
                self.contents[tag].append(part)
                if tag != self.current_tag:
                    self.current_tag = tag

    def from_xl(self, fname, xlrange=('A', 1, None)):
        '''
        accept an excel file, extract the calculations in it and incorporate
        it in the document.'''

        NS = {
            'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
            'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
            'x14ac': 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac',
        }

        with ZipFile(fname, 'r') as zin:
            sheet_xml = zin.read('xl/worksheets/sheet1.xml').decode('utf-8')
            str_xml = zin.read('xl/sharedStrings.xml').decode('utf-8')

        sheet_tree = ET.fromstring(sheet_xml)
        str_tree = ET.fromstring(str_xml)
        strs = [node[0].text for node in str_tree]

        # store calcs in dict with cell addreses as keys
        instructions = {}

        rows = sheet_tree.find('{%s}sheetData' % NS['main'])
        xlrange = (*xlrange[:2],
                   (xlrange[-1] if xlrange[-1] else int(rows[-1].attrib['r'])))

        for i, row in enumerate(rows):
            if xlrange[1] <= int(row.attrib['r']) <= xlrange[2]:
                line = []
                options = []
                current_key = f'para{i}'
                current_col = -1
                for col in row:
                    col_let = ''.join(
                        [c for c in col.attrib['r'] if c.isalpha()])
                    if col_let == xlrange[0]:
                        current_col = 0
                    if 0 <= current_col < 3:
                        cont = ['txt', '']
                        if 't' in col.attrib and col.attrib['t'] == 's':
                            cont = ['txt', strs[int(col[0].text)]]
                        elif col.findall('{%s}f' % NS['main']):
                            cont = ['expr', col[0].text, col[1].text]
                        elif len(col):
                            cont = ['val', col[0].text]

                        if current_col == 0:
                            line.append(cont)
                            current_col += 1
                        elif current_col == 1:
                            if line[0][0] == 'txt':
                                if cont[0] in ['expr', 'val']:
                                    line[0][0] = 'var'
                                    line[0][1] = f'"{line[0][1]}"'
                                    line.append(cont)
                                    current_key = col.attrib['r']
                                    current_col += 1
                        else:
                            if line[0][0] == 'var':
                                if cont[0] == 'txt':
                                    line.append(['opt', cont[1]])
                                    current_col += 1
                instructions[current_key] = line

        script = []
        for key, content in instructions.items():
            if content[0][0] == 'txt':
                para = content[0][1]
                script.append('# ' + para if para.strip() else '')
            elif content[0][0] == 'var':
                var_name = content[0][1]
                if len(content[1]) == 2:
                    steps = [content[1][1]]
                else:
                    cell_pat = re.compile(r'[A-Z]+[0-9]+')

                    def acceptable(i1, i2):
                        return cell_pat.sub(
                            lambda x: instructions[x.group(0)][i1][i2],
                            content[1][1]).replace('^', '**').lower()
                    steps = [acceptable(0, 1), acceptable(1, -1)]
                steps.append(content[1][-1])
                opt = content[-1][-1] if content[-1][0] == 'opt' else ''
                script.append(
                    '# ' + cal([var_name, steps, opt]).replace('\n', '\n# '))

        self.send('\n'.join(script))

    def from_normal(norm):
        '''
        accept an ascii input (equations) and comments without preceding with
        hash and send it as a python-legal input

        import statements and the like:
        :import this
        '''

        lines = norm.split('\n')
        py_lines = []
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

        self.send(py_legal)

    def write(self, outfile=None):
        '''replace all the tags with the contents of the python script.
        then if the destination file is given, write a typeset-ready latex
        file or another type of file (based on the extension, using pandoc).
        If the destination file is not given, perform an in-place
        substitution on the input file without destroying the chance of
        reverting changes. If this function is run on an in-place substituted
        file, it will revert the file to its original state (with tags).'''

        if not self.document_file:
            if outfile:
                ext = path.splitext(outfile)[1]
                self.document_file = self.file_handlers[ext](
                    None, self.to_clear)
            else:
                self.document_file = self.file_handlers['.tex'](
                    None, self.to_clear)

        self.document_file.write(outfile, self.contents)
        logger.info('SUCCESS!!!')
        self.log = self.log_recorder.log
