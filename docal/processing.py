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
# for status tracking
import logging
from typing import Iterable
from .calculation import cal, _process_options
from .parsing import UNIT_PF, eqn, mat_to_list, to_math, build_eqn, _get_parts, Comment
from .document import Tag

# default working area
DICT = {}

# the tag pattern
PATTERN = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')

LOG_FORMAT = '%(levelname)s: %(message)s'
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def find_name_targets(target) -> list[str]:
    targets = []
    if type(target) is ast.Tuple or type(target) is ast.List:
        for elem in target.elts:
            targets += find_name_targets(elem)
    elif type(target) is ast.Name:
        targets.append(target.id)
    elif isinstance(target, ast.Starred):
        targets += find_name_targets(target.value)
    else:
        # probably not useful to put in document
        pass
    return targets

class LogRecorder(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log = []

    def emit(self, record):
        self.log.append(self.format(record))


class processor:
    '''organize the process by taking tags from the filetype-specific handler objects,
    making a dictionary for them, and calling the write method of those objects
    giving them the dictionary

    syntax: an object with methods for math rendering like frac, rad...
    '''

    def __init__(self, syntax=None, tags: list[Tag] | None=None, log_level=None):
        '''initialize'''

        self.syntax = syntax
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
        # =========TAG HANDLING================
        self.current_tag = None
        if tags:
            self.tags = tags
            tag_props = {}
            for tag in tags:
                prop = (tag.block, tag.table)
                if tag_props.get(tag.name, prop) != prop:
                    raise ValueError(f'The same tag #{tag.name} cannot be used for different purposes.')
                tag_props[tag.name] = prop
                if tag.block and not tag.table:
                    self.current_tag = tag.name
                    break
        if self.current_tag is None:
            self.tags = None
            if tags is not None:
                logger.warning('There are no tags in the document')
        # =========CALCULATION================
        # the calculations corresponding to the tags
        self.contents = {}
        # working area
        self.working_dict = DICT
        # default calculation options
        self.default_options = _process_options('', syntax=self.syntax)
        self.working_dict['__DOCAL_OPTIONS__'] = self.default_options

    def send(self, content):
        '''add the content to the tag, which will be sent to the document.
        Where it will be inserted is decided by the most recent tag.'''

        for tag, part in self.process(content):
            if tag not in self.contents.keys():
                self.contents[tag] = []
            self.contents[tag].append(part)

    def process(self, parts): # exported
        processed = []
        tag_names = set()
        variable_tags: dict[str, Tag] = {}
        if self.tags is not None:
            for tag in self.tags:
                if tag.table or not tag.block:
                    variable_tags[tag.name] = tag
                else:
                    tag_names.add(tag.name)
        for part in _get_parts(parts):
            if isinstance(part, Comment):
                if part.kind == 'tag':
                    self.current_tag = part.content
                    logger.info('[Change tag] #%s', self.current_tag)
                    if self.tags and self.current_tag not in tag_names:
                        logger.warning('#' + self.current_tag + ' is not in the tags')
                elif part.kind == 'text':
                    for line in self._process_text(part.content):
                        processed.append((self.current_tag, line))
                elif part.kind in ['eqn-inline', 'eqn-disp']:
                    disp = part.kind == 'eqn-disp'
                    processed.append((self.current_tag, self._process_equation(part.content, disp)))
                elif part.kind == 'options':
                    # set options for calculations that follow
                    self.default_options = _process_options(part.content, syntax=self.syntax)
            elif isinstance(part, (ast.Assign, ast.Expr)):
                for proced in self._process_assignment(part):
                    processed.append((self.current_tag, proced))
            else:
                # if it does not appear like an equation or a comment,
                # just execute it
                logger.info('[Executing] line %s', part.lineno)
                co = compile(ast.Module([part], []), '<calculation>', 'exec')
                exec(co, self.working_dict)
                if isinstance(part, ast.Delete):
                    # also delete associated unit strings
                    for t in part.targets:
                        unit_var = t.id + UNIT_PF
                        if unit_var in self.working_dict:
                            del self.working_dict[unit_var]
        for tag in variable_tags.values():
            if not tag.table:
                processed.append((tag.name, ('inline', self._format_value(tag.name))))
                continue
            if tag.name not in self.working_dict:
                raise KeyError(f"'{tag.name}' is an undefined variable.")
            value = self.working_dict[tag.name]
            if not isinstance(value, Iterable):
                continue
            tbl_value = []
            for row in mat_to_list(value):
                if not isinstance(row, Iterable):
                    continue
                row_val = []
                for col in row:
                    row_val.append(self._format_value(tag.name, value=col))
                tbl_value.append(row_val)
            processed.append((tag.name, ('table', tbl_value)))

        return processed

    def _format_value(self, var, srnd=True, value=None):
        if var not in self.working_dict:
            raise KeyError(f"'{var}' is an undefined variable.")
        if value is None:
            value = self.working_dict[var]
            unit_name = var + UNIT_PF
            unit = to_math(self.working_dict[unit_name],
                           div="/",
                           working_dict=self.working_dict,
                           syntax=self.syntax,
                           ital=False) \
                if unit_name in self.working_dict.keys() and self.working_dict[unit_name] \
                and self.working_dict[unit_name] != '_' else ''
        else:
            unit = ''
        result = to_math(value, syntax=self.syntax)
        return build_eqn([[result + self.syntax.txt(self.syntax.halfsp) + unit]],
                         disp=False, vert=False, srnd=srnd,
                         syntax=self.syntax)

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
            equation = ('disp', eqn(line, syntax=self.syntax))
        else:
            equation = ('inline', eqn(line, disp=False, syntax=self.syntax))
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
        options = _process_options(line.options, self.default_options, self.syntax)
        result = cal(line,
                     self.working_dict,
                     syntax=self.syntax,
                     options=options)
        return [result] + [('text', '')] * options['newlines']

