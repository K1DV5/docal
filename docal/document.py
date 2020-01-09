# Written by K1DV5
'''
Module document

provides the document class to arrange processing the calculation
and inserting into the document
'''

import ast
# for tag replacements
import re
# for path manips
from os import path
# for status tracking
import logging
from .calculation import cal, _process_options
from .parsing import UNIT_PF, eqn, to_math, build_eqn, DEFAULT_MAT_SIZE, _get_parts, Comment

# default working area
DICT = {}

# the tag pattern
PATTERN = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')

LOG_FORMAT = '%(levelname)s: %(message)s'
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__name__)

class LogRecorder(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log = []

    def emit(self, record):
        self.log.append(self.format(record))


class document:
    '''organize the process by taking tags from the filetype-specific classes,
    making a dictionary for them, and calling the write method of those classes
    giving them the dictionary

    things required from handler class;
    * .__init__(self, infile: str, PATTERN: re.compiled?, to_clear: bool)
    * .syntax provider object property
    * list of .tags property already in the document
    * .write(self, outfile: str, values: dict) method (if writing)
    '''

    def __init__(self, infile=None, outfile=None, handler=None, to_clear=False, log_level=None, log_file=None, working_dict=DICT):
        '''initialize'''

        if handler is None:
            raise ValueError('File handler required.')
        self.syntax = handler.syntax
        self.to_clear = to_clear
        # ===========LOGGING==================
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
        if log_file is not None:
            file_logger = logging.FileHandler(log_file, 'w')
            file_logger.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(file_logger)
        if log_level:
            logger.setLevel(getattr(logging, log_level.upper()))
        # =========FILE HANDLING================
        if infile:
            infile = path.abspath(infile)
            basename, ext = path.splitext(infile)
            self.document_file = handler(infile, PATTERN, to_clear)
            # the calculations object that will convert given things to a list and store
            self.tags = self.document_file.tags
        elif outfile:
            ext = path.splitext(outfile)[1]
            self.document_file = handler(None, PATTERN, self.to_clear)
            self.tags = []
        else:
            raise ValueError('Need to specify at least one document')
        self.outfile = path.abspath(outfile) if outfile else None
        self.current_tag = self.tags[0] if self.tags else None
        if self.current_tag is None:
            logger.warning('There are no tags in the document')
        # =========CALCULATION================
        # the calculations corresponding to the tags
        self.contents = {}
        # working area
        self.working_dict = working_dict
        # default calculation options
        self.default_options = {
                    'steps': [],
                    'mat_size': DEFAULT_MAT_SIZE,
                    'unit': None,
                    'mode': 'default',
                    'vert': True,
                    'note': None,
                    'hidden': False,
                    'decimal': 3,
                    'result' : None,
                    'newlines': 0,
                }
        self.working_dict['__DOCAL_OPTIONS__'] = self.default_options

    def send(self, content):
        '''add the content to the tag, which will be sent to the document.
        Where it will be inserted is decided by the most recent tag.'''

        if not self.to_clear:
            for tag, part in self.process(content):
                if tag not in self.contents.keys():
                    self.contents[tag] = []
                self.contents[tag].append(part)

    def process(self, parts): # exported
        tag = self.current_tag
        processed = []
        for part in _get_parts(parts):
            if isinstance(part, Comment):
                if part.kind == 'tag':
                    tag = self.current_tag = part.content
                    logger.info('[Change tag] #%s', tag)
                elif part.kind == 'text':
                    for line in self._process_text(part.content):
                        processed.append((tag, line))
                elif part.kind in ['eqn-inline', 'eqn-disp']:
                    disp = part.kind == 'eqn-disp'
                    processed.append((tag, self._process_equation(part.content, disp)))
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
        if var in self.working_dict:
            unit_name = var + UNIT_PF
            unit = to_math(self.working_dict[unit_name],
                           div="/",
                           working_dict=self.working_dict,
                           syntax=self.syntax,
                           ital=False) \
                if unit_name in self.working_dict.keys() and self.working_dict[unit_name] \
                and self.working_dict[unit_name] != '_' else ''
            result = to_math(self.working_dict[var], syntax=self.syntax)
            return build_eqn([[result + self.syntax.txt(self.syntax.halfsp) + unit]],
                             disp=False, vert=False, srnd=srnd,
                             syntax=self.syntax)
        else:
            raise KeyError(f"'{var}' is an undefined variable.")

    def _process_text(self, line):
        '''
        convert comments to latex paragraphs
        '''
        # there may be more than one kind of part (inline equation, text)
        parts = []
        # switcher between inline equation and text part in the line
        ref = False
        for part in re.split(r'(?a)(#\w+)', line.strip()):
            if ref:
                parts.append(('inline', self._format_value(part[1:])))
                ref = False
            else:
                parts.append(('text', part))
                ref = True
        return parts

    def _process_equation(self, line, disp):

        # value reference pattern
        patt = r'(?a)#(\w+)'
        # term beginning with a number unlikely to be used, so that the \times
        # operators are not omitted like if it was a variable name
        pholder = '111.111**PLACEHOLDER00'
        # store the values in order
        vals = [self._format_value(v.group(1), False)
                for v in re.finditer(patt, line)]
        # replace all references by placeholder
        line = re.sub(patt, pholder, line)
        # process it
        if disp:
            equation = ('disp', eqn(line[2:], syntax=self.syntax))
        else:
            equation = ('inline', eqn(line[1:], disp=False, syntax=self.syntax))
        # put back the values in their order
        for v in vals:
            equation = (equation[0], equation[1].replace(to_math(pholder, syntax=self.syntax), v, 1))
        return equation

    def _process_assignment(self, line):
        '''
        evaluate assignments and convert to latex form
        '''
        logger.info('[Processing] line %s', line.lineno)
        # the cal function will execute it so no need for exec
        result = cal(line, self.working_dict, syntax=self.syntax)
        return (result[1], result[0])

    def write(self):
        '''
        tell the respective handler to write the file
        '''

        self.document_file.write(self.outfile, self.contents)
        logger.info('SUCCESS!!!')
        self.log = self.log_recorder.log
        return True
