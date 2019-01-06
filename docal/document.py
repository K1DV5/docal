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
from subprocess import run
# for temp folder access and path manips
from os import environ, remove, path, makedirs
# for timings
from datetime import datetime
# for colored output
try:
    from colorama import init as color_init
except ImportError:
    print('colorama not installed, using default color...\n')

    def color(text, clr):
        return text
else:
    color_init()
    COLORS = {'cyan': '36;1',
              'red': '31;1',
              'green': '32;1',
              'yellow': '33;1',
              'magenta': '35;1'}

    def color(text, clr):
        '''surround the text with the appropriate ANSI escape sequences
        so that they can be printed in color'''
        return f'\033[{COLORS[clr]}m{text}\033[0m'
# for working with the document's variables and filename
try:
    from __main__ import __file__ as DEFAULT_SCRIPT, __dict__ as DICT
except ImportError:
    DEFAULT_SCRIPT = None
    DICT = {}
from .calculation import cal
from .parsing import UNIT_PF, PARENS, eqn, latexify
# to log info about what it's doing with timestamps
START_TIME = datetime.now()


class document:
    '''contains the document handle'''

    # the tag pattern
    pattern = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')
    # the inline calculation pattern like #{x+5}
    inline_calc = re.compile(r'(?<![\w\\])#\{(.*?)\}')
    # surrounding of the content sent for reversing (something that
    # doesn't change the actual content of the document, and works inside lines)
    surrounding = ['{} {{ {}', '{} }} {}']
    # warning for tag place protection in document:
    warning = ('BELOW IS AN AUTO GENERATED LIST OF TAGS. '
               'DO NOT DELETE IT IF REVERSING IS DESIRED!!!\n%')
    # temp folder for converted files
    temp_dir = path.join(environ['TMP'], 'docal_tmp')
    # If it does not exist, create it
    makedirs(temp_dir, exist_ok=True)

    def _prepare_infile(self, infile):
        '''convert the input file to a tex file for easier manipulation which
        will then optionally be converted back to the input file. Currently
        works with word (.docx) files'''

        # file taken as input file when not explicitly set:
        if infile:
            self.infile = path.abspath(infile)
        else:
            self.infile = DEFAULT_SCRIPT.replace('.py', '.tex')
        try:
            if self.infile.endswith('.docx'):
                self.temp_file = path.join(
                    self.temp_dir, path.splitext(path.basename(infile))[0])
                pandoc = run(['pandoc', self.infile, '-t', 'latex', '-o',
                              self.temp_file, '--extract-media', self.temp_dir])
                if pandoc.returncode != 0:
                    raise FileNotFoundError('pandoc error')
                with open(self.temp_file) as file:
                    self.file_contents = file.read().replace('\\#\\#', '#')
            else:
                self.temp_file = 0
                with open(self.infile) as file:
                    self.file_contents = file.read()
        except FileNotFoundError:
            print(color('ERROR:', 'red'),
                  f'{color(path.basename(self.infile), "cyan")} cannot be found.')
            exit()

    def __init__(self, infile=None):
        '''initialize'''

        # convert if necessary
        self._prepare_infile(infile)
        # the calculation parts
        self.contents = {}
        # the collection of tags at the bottom of the file for reversing
        self.tagline = re.search(fr'\n% *{re.escape(self.warning)}'
                                 '*[\[[a-zA-Z0-9_ ]+\]\]',
                                 self.file_contents)
        if self.tagline:
            start = self.tagline.group(0).find('[[') + 2
            end = self.tagline.group(0).rfind(']]')
            self.tags = self.tagline.group(0)[start:end].split()
        else:
            self.tags = [tag.group(2)
                         for tag in self.pattern.finditer(self.file_contents)]
        # where the argument of the send function will go to
        self.current_tag = self.tags[0] if self.tags else None
        # temp storage for assignment statements where there are unmatched parens
        self.incomplete_assign = ''
        # temp storage for block statements like if and for
        self.incomplete_stmt = ''

    def _process_comment(self, line):
        '''
        convert comments to latex paragraphs
        '''

        print(color('    Processing comment line to a paragraph...', 'green'),
              color(str(datetime.time(datetime.now())), 'magenta'),
              f'\n        {line}')
        line = line.lstrip()[1:].strip()
        if line.startswith('$'):
            # inline calculations, accepted in #{...}
            calcs = [latexify(eval(x.group(1), DICT))
                     for x in self.inline_calc.finditer(line)]
            line = re.sub(r'(?a)#(\w+)',
                          lambda x: 'TMP0'.join(
                              x.group(1).split('_')) + 'TMP0',
                          line)
            line = self.inline_calc.sub('TMP0CALC000', line)
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
            augmented = self.pattern.sub(self._repl_bare, line)
            augmented = self.inline_calc.sub(lambda x:
                                             eqn(str(eval(x.group(1), DICT)),
                                                 disp=False), augmented)

        return augmented

    def _process_assignment(self, line):
        '''
        evaluate assignments and convert to latex form
        '''
        if self.incomplete_assign or \
                any([line.count(par[0]) != line.count(par[1])
                     for par in PARENS]):
            self.incomplete_assign += '\n' + line
            if all([self.incomplete_assign.count(par[0]) ==
                    self.incomplete_assign.count(par[1])
                    for par in PARENS]):
                line = self.incomplete_assign
                self.incomplete_assign = ''
            else:
                line = None
        if line:
            if not line.rstrip().endswith(';'):
                print(color('    Evaluating and converting equation line to'
                            'LaTeX form...', 'green'),
                      color(str(datetime.time(datetime.now())), 'magenta'),
                      f'\n        {line}')
                # the cal function will execute it so no need for exec
                return cal(line)

            # if it does not appear like an equation or a comment, just execute it
            print(color('    Executing statement...', 'green'), f'\n        {line}',
                  color(str(datetime.time(datetime.now())), 'magenta'))
            exec(line, DICT)
        return ''

    def _process_content(self, content):
        '''execute the actual content of the string in the context of the main
        script and return what will be sent to the document'''

        # if the first non-blank line is only #, do not modify
        hash_line = re.match(r'\s*#\s*\n', content)
        if hash_line:
            print(color('    Sending the content without modifying...', 'green'),
                  color(str(datetime.time(datetime.now())), 'magenta'))
            return content[hash_line.span()[1]:]
        sent = []
        for line in content.split('\n'):
            if any([line and not self.incomplete_assign and line[0].isspace(),
                    line and not line[0].isspace() and line[0] != '#'
                    and line.rstrip().endswith(':'),
                    not line and self.incomplete_stmt]):
                self.incomplete_stmt += '\n' + line
                line = None
            if line is not None:
                if self.incomplete_stmt:
                    print(color('    Executing statement...', 'green'),
                          f'\n        {self.incomplete_stmt}',
                          color(str(datetime.time(datetime.now())), 'magenta'))
                    exec(self.incomplete_stmt, DICT)
                    self.incomplete_stmt = ''
                # a real comment starts with ## and does nothing
                if line.lstrip().startswith('##'):
                    pass
                # if the first non whitespace char is # and not ## send as is
                # with the variables referenced with #var substituted
                elif line.lstrip().startswith('#'):
                    sent.append(self._process_comment(line))
                # if it is an assignment, take it as a calculation to send
                # unless it ends with a ;
                elif re.search(r'[^=]=[^=]', self.incomplete_assign + line):
                    sent.append(self._process_assignment(line))
                elif line:
                    # if it does not appear like an equation or a comment,
                    # just execute it
                    print(color('    Executing statement...', 'green'),
                          f'\n        {line}',
                          color(str(datetime.time(datetime.now())), 'magenta'))
                    exec(line, DICT)
                    if line.startswith('del '):
                        # also delete associated unit strings
                        variables = [v.strip()
                                     for v in line[len('del '):].split(',')]
                        for v in variables:
                            if v + UNIT_PF in DICT:
                                del DICT[v + UNIT_PF]
                else:
                    sent.append('')
        sent = '\n'.join(sent)
        return sent

    def _send(self, tag, content):
        '''store the conten as an item in the list under the tag
        for later substitution
        '''
        if tag == '_':
            tag = self.current_tag
        if tag in self.tags:
            if tag not in self.contents.keys():
                self.contents[tag] = []
            msgs = [color(tag, "cyan"), color(
                "Processing contents...", "green")]
            print(f'[{msgs[0]}]: {msgs[1]}',
                  color(str(datetime.time(datetime.now())), 'magenta'))
            self.contents[tag].append(self._process_content(content))
            if tag != self.current_tag:
                self.current_tag = tag
        else:
            print(color('ERROR:', 'red'),
                  f'Tag "{color(tag, "cyan")}" is not present in the document')
            exit()

    def send(self, content):
        '''add the content to the tag, which will be sent to the document.
        Where it will be inserted is decided by the most recent tag.'''

        tags = list(re.finditer(r'\n\s*#\w+\s*\n', content))
        tags_count = len(tags)
        # if there are tags mentioned
        if tags_count:
            # if no tag is specified at the start, send it to the current one
            tag_0_start = tags[0].span()[0] + 1
            content_before = content[:tag_0_start]
            if content_before.strip():
                self._send(self.current_tag, content_before)
            # for performance, define once
            content_len = len(content)
            for index, tag in enumerate(tags):
                # the content is between the end of the tag and either the
                # beginning of the next tag or the end of the string
                till = tags[index+1].span()[0] + 1 \
                    if index < tags_count - 1 else content_len
                tag_content = content[tag.span()[1]: till]
                tag = tag.group(0).strip()[1:]
                self._send(tag, tag_content)
        else:
            self._send(self.current_tag, content)

    def _repl(self, match_object, surround: bool):
        start, tag, end = [m if m else '' for m in match_object.groups()]
        if tag in self.contents.keys():
            result = '\n'.join(self.contents[tag])
        elif tag in DICT.keys():
            unit_name = tag + UNIT_PF
            unit = fr' \, \mathrm{{{latexify(DICT[unit_name], div_symbol="/")}}}'\
                if unit_name in DICT.keys() and DICT[unit_name] \
                and DICT[unit_name] != '_' else ''
            result = eqn(latexify(
                DICT[tag]) + unit, norm=False, disp=False)
        else:
            print(color('ERROR:', 'red'),
                  f"'{color(tag, 'cyan')}' is an undefined variable or an unused tag.")
            exit()

        if surround:
            return (start
                    + self.surrounding[0]
                    + (start if start == '\n' else '')
                    + result
                    + (end if end == '\n' else '')
                    + self.surrounding[1]
                    + end)

        return start + result + end

    def _repl_surround(self, match_object):
        return self._repl(match_object, True)

    def _repl_bare(self, match_object):
        return self._repl(match_object, False)

    def _revert_tags(self):
        # remove the tagline
        file_str = (self.file_contents[:self.tagline.start()].rstrip() +
                    self.file_contents[self.tagline.end():])
        # replace the sent regions with their respective tags
        for tag in self.tags:
            file_str = re.sub(r'(?s)'
                              + re.escape(self.surrounding[0])
                              + '.*?'
                              + re.escape(self.surrounding[1]),
                              '#' + tag, file_str, 1)
        # for inplace editing
        self.file_contents = file_str
        return file_str

    def _subs_in_place(self):
        file_str = self.file_contents + f'\n\n% {self.warning} [['
        for tag in self.tags:
            file_str += tag + ' '
        file_str = self.pattern.sub(self._repl_surround, file_str)
        file_str = file_str.rstrip('\n') + ']]'
        return file_str

    def _subs_separate(self):
        return self.pattern.sub(self._repl_bare, self.file_contents)

    def _prepare(self, outfile, revert):  # outfile needed for conditional
        '''prepare what will be written to the final file'''

        if outfile == self.infile:
            if revert:
                if self.tagline:
                    file_contents = self._revert_tags()
                else:
                    file_contents = self._subs_in_place()
            else:
                if self.tagline:
                    file_contents = self._revert_tags()
                file_contents = self._subs_in_place()

        else:
            if self.tagline:
                file_contents = self._revert_tags()
            file_contents = self._subs_separate()

        return file_contents

    def write(self, outfile_or_revert=None):
        '''replace all the tags with the contents of the python script.
        then if the destination file is given, write a typeset-ready latex
        file or another type of file (based on the extension, using pandoc).
        If the destination file is not given, perform an in-place
        substitution on the input file without destroying the chance of
        reverting changes. If this function is run on an in-place substituted
        file, it will revert the file to its original state (with tags).'''

        revert = 1
        if outfile_or_revert == 0:
            revert = False
            outfile = self.infile[:-len('.docx')] + '-out.docx' \
                if self.infile.endswith('.docx') \
                else self.infile
        elif not outfile_or_revert:
            outfile = self.infile[:-len('.docx')] + '-out.docx' \
                if self.infile.endswith('.docx') \
                else self.infile
        else:
            outfile = outfile_or_revert

        print((f'{color("Writing output to", "green")} '
               f'{color(outfile, "cyan")}{color("...", "green")}'),
              color(datetime.now(), "magenta"))

        file_contents = self._prepare(outfile, revert)

        # if the input is a word file
        if self.temp_file:
            # use pandoc to yield the desired file
            with open(self.temp_file, 'w') as tmp:
                tmp.write(file_contents)
            pandoc = run(['pandoc', '-f', 'latex', self.temp_file,
                          '-o', outfile, '--reference-doc', self.infile])
            if pandoc.returncode != 0:
                print(color('ERROR:', 'red'),
                      color((f'{path.basename(outfile)} is currently open'
                             'in another application), possibly Word'), 'red'))
                exit()
            remove(self.temp_file)
        else:
            with open(outfile, 'w') as file:
                file.write(file_contents)

        print((f'\n{color("SUCCESS!!!", "green")}     '
               f'(finished in {color(str(datetime.now() - START_TIME), "magenta")})'))
