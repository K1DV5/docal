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
# the inline calculation pattern like #{x+5}
INLINE_CALC = re.compile(r'(?<![\w\\])#\{(.*?)\}')
# surrounding of the content sent for reversing (something that doesn't
# change the actual content of the document, and works inside lines)
SURROUNDING = ['{} {{ {}', '{} }} {}']


def _prepare_infile(infile, temp_dir):
    '''convert the input file to a tex file for easier manipulation which
    will then optionally be converted back to the input file. Currently
    works with word (.docx) files'''

    # file taken as input file when not explicitly set:
    if infile:
        infile = path.abspath(infile)
    else:
        infile = DEFAULT_SCRIPT.replace('.py', '.tex')
    if infile.endswith('.docx'):
        temp_file = path.join(
            temp_dir, path.splitext(path.basename(infile))[0])
        pandoc = run(['pandoc', infile, '-t', 'latex', '-o',
                      temp_file, '--extract-media', temp_dir])
        if pandoc.returncode != 0:
            raise FileNotFoundError('pandoc error')
        with open(temp_file) as file:
            file_contents = file.read().replace('\\#\\#', '#')
    else:
        temp_file = 0
        with open(infile) as file:
            file_contents = file.read()

    return infile, temp_file, file_contents


def _repl(match_object, surround: bool, contents: dict = {}):
    start, tag, end = [m if m else '' for m in match_object.groups()]
    if tag in contents:
        result = '\n'.join(contents[tag])
    elif tag in DICT:
        unit_name = tag + UNIT_PF
        unit = fr' \, \mathrm{{{latexify(DICT[unit_name], div_symbol="/")}}}'\
            if unit_name in DICT.keys() and DICT[unit_name] \
            and DICT[unit_name] != '_' else ''
        result = eqn(latexify(
            DICT[tag]) + unit, norm=False, disp=False)
    else:
        raise KeyError(
            f"'{tag}' is an undefined variable or an unused tag.")

    if surround:
        return (start
                + SURROUNDING[0]
                + (start if start == '\n' else '')
                + result
                + (end if end == '\n' else '')
                + SURROUNDING[1]
                + end)

    return start + result + end


def _process_comment(line, content_dict: dict):
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
        augmented = PATTERN.sub(lambda x: _repl(x, False, content_dict), line)
        augmented = INLINE_CALC.sub(lambda x:
                                    eqn(str(eval(x.group(1), DICT)),
                                        disp=False), augmented)

    return augmented


def _process_assignment(line):
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


class document:
    '''contains the document handle'''

    # warning for tag place protection in document:
    warning = ('BELOW IS AN AUTO GENERATED LIST OF TAGS. '
               'DO NOT DELETE IT IF REVERSING IS DESIRED!!!\n%')
    # temp folder for converted files
    temp_dir = path.join(environ['TMP'], 'docal_tmp')
    # If it does not exist, create it
    makedirs(temp_dir, exist_ok=True)

    def __init__(self, infile=None, to_clear=False):
        '''initialize'''

        # convert if necessary
        [self.infile, self.temp_file,
         self.file_contents] = _prepare_infile(infile, self.temp_dir)
        # whether the input file is supposed to be cleared of calculations
        self.to_clear = to_clear
        # the calculation parts
        self.contents = {}
        # the collection of tags at the bottom of the file for reversing
        self.tagline = re.search(fr'\n% *{re.escape(self.warning)}'
                                 '*[\[[a-zA-Z0-9_ ]+\]\]',
                                 self.file_contents)
        # remove previous calculation parts
        if self.tagline:
            start = self.tagline.group(0).find('[[') + 2
            end = self.tagline.group(0).rfind(']]')
            self.tags = self.tagline.group(0)[start:end].split()
            self._revert_tags()
        self.tags = [tag.group(2)
                     for tag in PATTERN.finditer(self.file_contents)]
        # where the argument of the send function will go to
        self.current_tag = self.tags[0] if self.tags else None
        # temp storage for assignment statements where there are unmatched parens
        self.incomplete_assign = ''
        # temp storage for block statements like if and for
        self.incomplete_stmt = ''

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
                    self._send(tag, _process_assignment(part[0]))
                elif part[1] == 'comment':
                    self._send(tag, _process_comment(part[0], self.contents))
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

    def _subs_in_place(self):
        file_str = self.file_contents + f'\n\n% {self.warning} [['
        for tag in self.tags:
            file_str += tag + ' '
        file_str = PATTERN.sub(lambda x: _repl(x, True, self.contents),
                               file_str)
        file_str = file_str.rstrip('\n') + ']]'
        return file_str

    def _subs_separate(self):
        return PATTERN.sub(lambda x: _repl(x, False, self.contents),
                           self.file_contents)

    def write(self, outfile=None):
        '''replace all the tags with the contents of the python script.
        then if the destination file is given, write a typeset-ready latex
        file or another type of file (based on the extension, using pandoc).
        If the destination file is not given, perform an in-place
        substitution on the input file without destroying the chance of
        reverting changes. If this function is run on an in-place substituted
        file, it will revert the file to its original state (with tags).'''

        if not outfile:
            if self.infile.endswith('.docx'):
                basename, ext = path.splitext(self.infile)
                outfile = basename + '-out' + ext
            else:
                outfile = self.infile
        if not self.to_clear:
            if path.abspath(outfile) == path.abspath(self.infile) \
                    and self.infile.endswith('.tex'):
                self.file_contents = self._subs_in_place()
            else:
                self.file_contents = self._subs_separate()

        print(f"Writing output to '{outfile}'... {datetime.now()}")

        file_contents = self.file_contents

        # if the input is a word file
        if self.temp_file:
            # use pandoc to yield the desired file
            with open(self.temp_file, 'w') as tmp:
                tmp.write(file_contents)
            pandoc = run(['pandoc', '-f', 'latex', self.temp_file,
                          '-o', outfile, '--reference-doc', self.infile])
            if pandoc.returncode != 0:
                raise RuntimeWarning(f"'{path.basename(outfile)}' may be"
                                     "currently open in another application, possibly Word")
            remove(self.temp_file)
        else:
            with open(outfile, 'w') as file:
                file.write(file_contents)

        print(f'\nSUCCESS!!!     (finished in {datetime.now() - START_TIME})')
