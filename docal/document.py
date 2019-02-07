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
# for temp folder access and path manips
from os import environ, remove, path, makedirs
# for timings
from datetime import datetime
# for word file handling
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
from shutil import move
# for working with the document's variables and filename
try:
    from __main__ import __file__ as DEFAULT_SCRIPT, __dict__ as DICT
except ImportError:
    DEFAULT_SCRIPT = None
    DICT = {}
from .calculation import cal
from .parsing import UNIT_PF, eqn, latexify
# to split the calculation string
from .utils import _split_module
# to log info about what it's doing with timestamps
START_TIME = datetime.now()
# the tag pattern
PATTERN = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')
PATTERN_2 = re.compile(r'(?s)([^\w\\]|^)##(\w+?)(\W|$)')  # for word
# the inline calculation pattern like #{x+5}
INLINE_CALC = re.compile(r'(?<![\w\\])#\{(.*?)\}')
# surrounding of the content sent for reversing (something that doesn't
# change the actual content of the document, and works inside lines)
SURROUNDING = ['{} {{ {}', '{} }} {}']


class latexFile:
    '''handles the latex files'''

    # warning for tag place protection in document:
    warning = ('BELOW IS AN AUTO GENERATED LIST OF TAGS. '
               'DO NOT DELETE IT IF REVERSING IS DESIRED!!!\n%')

    def __init__(self, infile, to_clear):

        if infile:
            self.infile = path.abspath(infile)
        else:
            self.infile = DEFAULT_SCRIPT.replace('.py', '.tex')
        self.to_clear = to_clear
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
        for tag in self.tags:
            file_str += tag + ' '
        file_str = PATTERN.sub(lambda x: self._repl(x, True, values),
                               file_str)
        file_str = file_str.rstrip('\n') + ']]'
        return file_str

    def _subs_separate(self, values: dict):
        return PATTERN.sub(lambda x: self._repl(x, False, values),
                           self.file_contents)

    def _repl(self, match_object, surround: bool, values: dict):
        start, tag, end = [m if m else '' for m in match_object.groups()]
        if tag in values:
            result = '\n'.join(values[tag])
        else:
            raise KeyError(f"'{tag}' is an unused tag.")

        if surround:
            return (start
                    + SURROUNDING[0]
                    + (start if start == '\n' else '')
                    + result
                    + (end if end == '\n' else '')
                    + SURROUNDING[1]
                    + end)

        return start + result + end

    def write(self, outfile=None, values={}):
        if not outfile:
            outfile = self.infile
        if not self.to_clear:
            if path.abspath(outfile) == path.abspath(self.infile):
                self.file_contents = self._subs_in_place(values)
            else:
                self.file_contents = self._subs_separate(values)

        print(f"Writing output to '{outfile}'... {datetime.now()}")
        with open(outfile, 'w') as file:
            file.write(self.file_contents)


class wordFile:

    # temp folder for converted files
    temp_dir = path.join(environ['TMP'], 'docal_tmp')
    # If it does not exist, create it
    makedirs(temp_dir, exist_ok=True)
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

    def __init__(self, infile, to_clear=False):
        # file taken as input file when not explicitly set:
        self.infile = infile
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
        self.tags = [info['tag'][1] for info in self.tags_info]

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
                        if '##' in cont[0]:
                            # there is some tag in this; ignore any properties
                            w_r = ET.SubElement(child, pref_w + 'r')
                            w_t = ET.SubElement(w_r, pref_w + 't',
                                                {'xml:space': 'preserve'})
                            w_t.text = cont[0]
                            # store full info about the tags
                            for tag in PATTERN_2.findall(cont[0]):
                                if cont[0].strip() == '##' + tag[1]:
                                    position = 'para'
                                else:
                                    position = 'inline'
                                tags_info.append({'tag': tag,
                                                  'address': [child, w_r, w_t],
                                                  'position': position,
                                                  'index': index})
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
        ranges = zip([i + 1 for i in indices], indices[1:] + [ans_len])

        added = 0  # the added index to make up for the added elements
        for index, (start, end) in enumerate(ranges):
            info = self.tags_info[index]
            ans_parts = ans_tree[0][start: end]
            if info['position'] == 'para':
                ans_parts.reverse()  # because they are inserted at the same index
                for ans in ans_parts:
                    self.doc_tree[0].insert(info['index'] + added, ans)
                self.doc_tree[0].remove(info['address'][0])
                added += len(ans_parts) - 1  # minus the tag para (removed)
            else:
                loc_para, loc_run, loc_text = info['address']
                split_text = loc_text.text.split('##' + info['tag'][1], 1)
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

    def _get_ans_tree(self, values={}):
        result_str = '\n\n'.join(['##' + tag + '\n\n' + '\n'.join(values[tag])
                                  for tag in self.tags])
        result_tex = path.join(
            self.temp_dir, path.basename(self.infile) + '-res.tex')
        result_docx = path.splitext(result_tex)[0] + '.docx'
        with open(result_tex, 'w') as file:
            file.write(result_str)
        run(['pandoc', result_tex, '-o', result_docx])
        with ZipFile(result_docx) as docx:
            ans_tree = ET.fromstring(docx.read('word/document.xml'))
        remove(result_tex)
        remove(result_docx)

        return ans_tree

    def write(self, outfile=None, values={}):

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

        if not outfile:
            base, ext = path.splitext(self.infile)
            outfile = base + '-out' + ext
        move(tmp_fname, outfile)


class document:
    '''organize the process by taking tags from the filetype-specific classes,
    making a dictionary for them, and calling the write method of those classes
    giving them the dictionary'''

    file_handlers = {
        '.docx': wordFile,
        '.tex': latexFile,
    }

    def __init__(self, infile=None, to_clear=False):
        '''initialize'''

        # the document
        if infile:
            infile = path.abspath(infile)
            ext = path.splitext(infile)[1]
            self.document_file = self.file_handlers[ext](infile, to_clear)
        else:
            self.document_file = latexFile(
                DEFAULT_SCRIPT.replace('.py', '.tex'), to_clear)
        self.tags = self.document_file.tags
        self.to_clear = to_clear
        # the calculations corresponding to the tags
        self.contents = {}
        self.current_tag = self.tags[0] if self.tags else None
        # temp storage for assignment statements where there are unmatched parens
        self.incomplete_assign = ''
        # temp storage for block statements like if and for
        self.incomplete_stmt = ''

    def _format_value(self, var):
        if var in DICT:
            unit_name = var + UNIT_PF
            unit = fr' \, \mathrm{{{latexify(DICT[unit_name], div_symbol="/")}}}'\
                if unit_name in DICT.keys() and DICT[unit_name] \
                and DICT[unit_name] != '_' else ''
            result = eqn(latexify(
                DICT[var]) + unit, norm=False, disp=False)
        else:
            raise KeyError(f"'{var}' is an undefined variable.")

        return result

    def _process_comment(self, line, content_dict: dict):
        '''
        convert comments to latex paragraphs
        '''

        print('    Processing comment line to a paragraph...',
              str(datetime.time(datetime.now())),
              f'\n        {line}')
        if line.startswith('$'):
            # inline calculations, accepted in #{...}
            calcs = [latexify(eval(x.group(1), DICT))
                     for x in INLINE_CALC.finditer(line)]
            line = re.sub(r'(?a)#(\w+)',
                          lambda x: 'TMP0'.join(
                              x.group(1).split('_')) + 'TMP0',
                          line)
            line = INLINE_CALC.sub('TMP0CALC000', line)
            if line.startswith('$$'):
                line = eqn(*line[2:].split('|'))
            else:
                line = eqn(line[1:], disp=False)
            augmented = re.sub(r'(?a)\\mathrm\s*\{\s*(\w+)TMP0\s*\}',
                               lambda x: latexify(
                                   DICT['_'.join(x.group(1).split('TMP0'))]),
                               line)
            for calc in calcs:
                augmented = re.sub(r'(?a)\\mathrm\s*\{\s*TMP0CALC000\s*\}',
                                   calc.replace('\\', r'\\'), augmented, 1)
        else:
            augmented = PATTERN.sub(lambda x: x.group(1) +
                                    self._format_value(x.group(2)) +
                                    x.group(3), line)
            augmented = INLINE_CALC.sub(lambda x:
                                        eqn(str(eval(x.group(1), DICT)),
                                            disp=False), augmented)

        return augmented

    def _process_assignment(self, line):
        '''
        evaluate assignments and convert to latex form
        '''
        if not line.rstrip().endswith(';'):
            print('    Evaluating and converting equation line to'
                  'LaTeX form...',
                  str(datetime.time(datetime.now())),
                  f'\n        {line}')
            # the cal function will execute it so no need for exec
            return cal(line)
        else:
            # if it does not appear like an equation or a comment, just execute it
            print('    Executing statement...', f'\n        {line}',
                  str(datetime.time(datetime.now())),)
            exec(line, DICT)
        return ''

    def _send(self, tag, content):
        '''store the conten as an item in the list under the tag
        for later substitution
        '''
        if tag == '_':
            tag = self.current_tag
        if tag in self.tags:
            if tag not in self.contents.keys():
                self.contents[tag] = []
            self.contents[tag].append(content)
            if tag != self.current_tag:
                self.current_tag = tag
        else:
            raise KeyError(f'Tag {tag} cannot be found in the document')

    def send(self, content):
        '''add the content to the tag, which will be sent to the document.
        Where it will be inserted is decided by the most recent tag.'''

        if not self.to_clear:
            tag = self.current_tag
            print(f'[{tag}]: Processing contents...',
                  str(datetime.time(datetime.now())))
            for part in _split_module(content):
                if part[1] == 'tag':
                    tag = part[0]
                    print(f'[{tag}]: Processing contents...',
                          str(datetime.time(datetime.now())))
                elif part[1] == 'assign':
                    self._send(tag, self._process_assignment(part[0]))
                elif part[1] == 'comment':
                    self._send(tag, self._process_comment(
                        part[0], self.contents))
                elif part[1] == 'stmt':
                    # if it does not appear like an equation or a comment,
                    # just execute it
                    print('    Executing statement...',
                          f'\n        {part[0]}',
                          str(datetime.time(datetime.now())))
                    exec(part[0], DICT)
                    if part[0].startswith('del '):
                        # also delete associated unit strings
                        variables = [v.strip()
                                     for v in part[0][len('del '):].split(',')]
                        for v in variables:
                            if v + UNIT_PF in DICT:
                                del DICT[v + UNIT_PF]

    def write(self, outfile=None):
        '''replace all the tags with the contents of the python script.
        then if the destination file is given, write a typeset-ready latex
        file or another type of file (based on the extension, using pandoc).
        If the destination file is not given, perform an in-place
        substitution on the input file without destroying the chance of
        reverting changes. If this function is run on an in-place substituted
        file, it will revert the file to its original state (with tags).'''

        # treat the rest of the tags as values to be referred
        if not self.to_clear:
            for tag in self.tags:
                if tag not in self.contents:
                    self.contents[tag] = [self._format_value(tag)]

        self.document_file.write(outfile, self.contents)
        print(f'\nSUCCESS!!!     (finished in {datetime.now() - START_TIME})')
