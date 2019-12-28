# Written by K1DV5
'''
Module document

provides the document class

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

import ast
# for tag replacements
import re
# for path manips
from os import path
# for word file handling
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED
# for temp directory
import tempfile
# for status tracking
import logging
# for included word template access
from pkg_resources import resource_filename
from shutil import move, rmtree
from .calculation import cal, _process_options
from .parsing import UNIT_PF, eqn, to_math, build_eqn, select_syntax, DEFAULT_MAT_SIZE, _get_parts, Comment

# default working area
DICT = {}

DEFAULT_FILE = 'Untitled.tex'
# the tag pattern
PATTERN = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')
# for excel file handling
NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'x14ac': 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac',
}
# surrounding of the content sent for reversing (something that doesn't
# change the actual content of the document, and works inside lines)
SURROUNDING = ['{} {{ {}', '{} }} {}']
EXCEL_SEP = '|'

LOG_FORMAT = '%(levelname)s: %(message)s'
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class calculations:
    '''
    accept an excel file, extract the calculations in it and incorporate
    it in the document.'''

    def __init__(self, tags, doc_type, working_dict):
        self.tags = tags
        self.current_tag = self.tags[0] if self.tags else None
        if self.current_tag is None:
            logger.warning('There are no tags in the document')
        self.doc_type = doc_type
        # for temp saving states
        self.temp_var = {}
        self.working_dict = working_dict
        # default calculation options
        self.default_options = {
                    'steps': [],
                    'mat_size': DEFAULT_MAT_SIZE,
                    'unit': '',
                    'mode': 'default',
                    'vert': True,
                    'note': None,
                    'hidden': False,
                    'decimal': 3,
                    'result' : None,
                    'newlines': 0
                }
        self.working_dict['__DOCAL_OPTIONS__'] = self.default_options

    def process(self, what, typ='python'):
        if typ == 'python':
            return self.process_content(what)
        elif typ == 'dcl':
            processed = []
            doc_tree = ET.fromstring(what)
            for child in doc_tree:
                if child.tag in ('ascii', 'python'):
                    if child.tag == 'ascii':
                        child.text = self.repl_asc(child.text)
                    for part in self.process_content(child.text):
                        processed.append(part)
                elif child.tag == 'excel':
                    for part in self.repl_xl(child.text):
                        processed.append(part)
            return processed
        elif typ == 'ascii':
            return self.process_content(self.repl_asc(what))
        elif typ == 'excel':
            # assuming what is a dict
            return self.xl_convert(**what)

    def process_content(self, parts): # exported
        tag = self.current_tag
        processed = []
        for part in _get_parts(parts):
            if isinstance(part, Comment):
                if part.kind == 'tag':
                    tag = self.current_tag = part[0]
                    logger.info('[Change tag] #%s', tag)
                elif part.kind == 'text':
                    for line in self._process_comment(part.content):
                        processed.append((tag, line))
                elif part.kind == 'options':
                    # set options for calculations that follow
                    self.working_dict['__DOCAL_OPTIONS__'] = \
                            _process_options(part.content, self.default_options)
            elif isinstance(part, ast.Assign):
                processed.append((tag, self._process_assignment(part)))
            elif isinstance(part, ast.Expr):
                processed.append((tag, self._process_assignment(part)))
            else:
                # if it does not appear like an equation or a comment,
                # just execute it
                logger.info('[Executing] line %s', part.lineno)
                co = compile(ast.Module([part], []), '<calculation>', 'exec')
                exec(co, globals())
                if isinstance(part, ast.Delete):
                    # also delete associated unit strings
                    for t in part.targets:
                        unit_var = t.id + UNIT_PF
                        if unit_var in self.working_dict:
                            del self.working_dict[unit_var]

        return processed

    def _format_value(self, var, srnd=True):
        syntax = select_syntax(self.doc_type)
        if var in self.working_dict:
            unit_name = var + UNIT_PF
            unit = to_math(self.working_dict[unit_name],
                           div="/",
                           working_dict=self.working_dict,
                           typ=self.doc_type,
                           ital=False) \
                if unit_name in self.working_dict.keys() and self.working_dict[unit_name] \
                and self.working_dict[unit_name] != '_' else ''
            result = to_math(self.working_dict[var], typ=self.doc_type)
            return build_eqn([[result + syntax.txt.format(syntax.halfsp) + unit]],
                             disp=False, vert=False, srnd=srnd,
                             typ=self.doc_type)
        else:
            raise KeyError(f"'{var}' is an undefined variable.")

    def _process_comment(self, line):
        '''
        convert comments to latex paragraphs
        '''

        logger.info('[Processing] %s', line)
        if line.startswith('$'):
            patt = r'(?a)#(\w+)'
            # term beginning with a number unlikely to be used
            pholder = '111.111**PLACEHOLDER00'
            vals = []
            for v in re.finditer(patt, line):
                vals.append(self._format_value(v.group(1), False))
            line = re.sub(patt, pholder, line)
            if line.startswith('$$'):
                line = ('disp', eqn(line[2:], typ=self.doc_type))
            else:
                line = ('inline', eqn(line[1:], disp=False, typ=self.doc_type))
            for v in vals:
                line[1] = line[1].replace(to_math(pholder, typ=self.doc_type), v, 1)
            parts = [line]
        else:
            parts = []
            ref = False
            for part in re.split(r'(?a)(#\w+)', line.strip()):
                if ref:
                    parts.append(('inline', self._format_value(part[1:])))
                    ref = False
                else:
                    parts.append(('text', part))
                    ref = True
        return parts

    def _process_assignment(self, line):
        '''
        evaluate assignments and convert to latex form
        '''
        logger.info('[Processing] line %s', line.lineno)
        # the cal function will execute it so no need for exec
        result = cal(line, self.working_dict, typ=self.doc_type)
        return (result[1], result[0])


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

    def __init__(self, infile=None, outfile=None, to_clear=False, log_level=None, log_file=False, working_dict=DICT):
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
            # the calculations object that will convert given things to a list and store
            self.calc = calculations(self.document_file.tags, self.document_file.name, DICT)
            if log_file:
                file_logger = logging.FileHandler(basename + '.log', 'w')
                file_logger.setFormatter(logging.Formatter(LOG_FORMAT))
                logger.addHandler(file_logger)
        elif outfile:
            ext = path.splitext(outfile)[1]
            self.document_file = self.file_handlers[ext](
                None, self.to_clear)
            self.calc = calculations([], self.document_file.name, working_dict)
        else:
            raise ValueError('Need to specify at least one document')
        if outfile:
            self.outfile = outfile
        else:
            self.outfile = None
        if log_level:
            logger.setLevel(getattr(logging, log_level.upper()))
        # the calculations corresponding to the tags
        self.contents = {}

    def send(self, content, typ='python'):
        '''add the content to the tag, which will be sent to the document.
        Where it will be inserted is decided by the most recent tag.'''

        if not self.to_clear:
            for tag, part in self.calc.process(content, typ):
                if tag not in self.contents.keys():
                    self.contents[tag] = []
                self.contents[tag].append(part)

    def write(self):
        '''replace all the tags with the contents of the python script.
        then if the destination file is given, write a typeset-ready latex
        file or word file.
        If the destination file is not given, perform an in-place
        substitution on the input file without destroying the chance of
        reverting changes. If this function is run on an in-place substituted
        file, it will revert the file to its original state (with tags).'''

        self.document_file.write(self.outfile, self.contents)
        logger.info('SUCCESS!!!')
        self.log = self.log_recorder.log
