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

import re
from subprocess import run
# for temp folder access and path manips
from os import environ, remove, path
from __main__ import __file__, __dict__
from .equation import _surround_equation as srnd, eqn
from .formatting import format_quantity
from .calculation import cal, _assort_input
from .parsing import UNIT_PF


class document:
    '''contains the document handle'''

    def _prepare_infile(self, infile):
        '''convert the input file to a tex file for easier manipulation which
        will then optionally be converted back to the input file. Currently
        works with word (.docx) files'''

        # file taken as input file when not explicitly set:
        self.infile = path.abspath(
            infile) if infile else __file__.replace('.py', '.tex')
        if self.infile.endswith('.docx'):
            self.temp_dir = path.join(environ['TMP'], 'docal_tmp')
            self.temp_file = path.join(
                self.temp_dir, path.basename(infile)[:infile.rfind('.')])
            run(['pandoc', self.infile, '-t', 'latex', '-o',
                 self.temp_file, '--extract-media', self.temp_dir])
            with open(self.temp_file) as file:
                original = file.read()
            self.file_contents = original.replace('\\#\\#', '#')
            with open(self.temp_file, 'w') as file:
                file.write(self.file_contents)
        else:
            self.temp_file = 0
            with open(self.infile) as file:
                self.file_contents = file.read()

    def __init__(self, infile=None):
        '''initialize'''
        # convert if necessary
        self._prepare_infile(infile)
        # the tag pattern
        self.pattern = re.compile(
            r'(?s)[^a-zA-Z0-9_\\]#[a-zA-Z_][a-zA-Z0-9_]*?[^a-zA-Z0-9_]')
        # the calculation parts
        self.contents = {}
        if self.infile.endswith('.tex'):
            separator = re.search(
                r'\\begin\s*{\s*document\s*}', self.file_contents)
            self.preamble = self.file_contents[:separator.span()[0]]
            self.body = self.file_contents[separator.span()[0]:]
        else:
            self.preamble = ''
            self.body = self.file_contents
        # surrounding of the content sent for reversing (something that
        # doesn't change the actual content of the document, and works inside lines)
        self.surrounding = ['{} {{ {}', '{} }} {}']
        # warning for tag place protection in document:
        self.warning = ('BELOW IS AN AUTO GENERATED LIST OF TAGS. '
                        'DO NOT DELETE IT IF REVERSING IS DESIRED!!!\n%')
        # the collection of tags at the bottom of the file for reversing
        self.tagline = re.search(fr'\n% *{re.escape(self.warning)} *[\[[a-zA-Z0-9_ ]+\]\]',
                                 self.file_contents)
        if self.tagline:
            start = self.tagline.group(0).find('[[') + 2
            end = self.tagline.group(0).rfind(']]')
            self.tags = self.tagline.group(0)[start:end].split()
        else:
            self.tags = [tag[2:-1]
                         for tag in self.pattern.findall(self.file_contents)]
        # where the argument of the send function will go to
        self.current_tag = self.tags[0] if self.tags else None

    def _exec_and_fmt(self, content):
        '''execute the actual content of the string in the context of the main script
        and return what will be sent to the document'''

        # if the first non-blank line is only #, do not modify
        hash_line = re.match(r'\s*#\s*\n', content)
        if hash_line:
            return content[hash_line.span()[1]:]
        sent = []
        for line in content.split('\n'):
            # if the first non whitespace char is # and not ## send as is
            # with the variables referenced with #var substituted
            if re.match(r'\s*#[^#]', line):
                line = line.lstrip()[1:].strip()
                if line.startswith('$'):
                    line = re.sub(r'#(\w+?)\b', '\g<1>00temp00', line)
                    if line.startswith('$$'):
                        line = eqn(*line[2:].split('|'))
                    else:
                        line = eqn(line[1:], disp=False)
                    sent.append(re.sub(r'\\mathrm\s*\{\s*(\w+)00temp00\s*\}',
                                       lambda x: format_quantity(
                                           __dict__[x.group(1)]), line))
                else:
                    sent.append(self.pattern.sub(
                        self._repl_bare, line.strip()[1:]))
            # if it is an assignment, take it as a calculation to send unless it ends with a ;
            elif re.search(r'[^=]=[^=]', line) and not line.rstrip().endswith(';'):
                main_var, irrelevant, unit = _assort_input(line.strip())[:3]
                sent.append(cal(line))
                # carry out normal op in main script
                exec(line, __dict__)
                # for later unit retrieval
                if unit:
                    exec(f'{main_var}{UNIT_PF} = "{unit}"', __dict__)
            # if it does not appear like an equation or a comment, just execute it
            elif line.strip():
                exec(line, __dict__)
        sent = '\n'.join(sent)
        return sent

    def _send(self, tag, content):
        '''store the conten as an item in the list under the tag
        for later substitution
        '''
        if tag == '_':
            tag = self.tags[self.tags.index(self.current_tag) - 1]
        if tag in self.tags:
            if tag not in self.contents.keys():
                self.contents[tag] = []
            self.contents[tag].append(self._exec_and_fmt(content))
            current_index = self.tags.index(self.current_tag)
            if current_index < len(self.tags) - 1:
                self.current_tag = self.tags[current_index + 1]
        else:
            raise UserWarning(f'Tag "{tag}" is not present in the document')

    def send(self, content):
        '''add the content to the tag, which will be sent to the document.
        Where it will be inserted is decided by the most recent tag.'''

        tags = list(re.finditer(r'\n\s*#\w+\s*\n', content))
        tags_count = len(tags)
        if tags_count:
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
        tag = match_object.group(0)[2:-1]
        ends = match_object.group(0)[0], match_object.group(0)[-1]
        if tag in self.contents.keys():
            result = '\n'.join(self.contents[tag])
        elif tag in __dict__.keys():
            unit_name = tag + UNIT_PF
            unit = __dict__[unit_name] if unit_name in __dict__.keys() else ''
            result = srnd(format_quantity(__dict__[tag]) + unit, False)
        else:
            raise UserWarning(f"There is nothing to send to tag '{tag}'.")

        if surround:
            start = ends[0] if ends[0] == '\n' else ''
            end = ends[1] if ends[1] == '\n' else ''
            return (ends[0]
                    + self.surrounding[0]
                    + start
                    + result
                    + end
                    + self.surrounding[1]
                    + ends[1])

        return ends[0] + result + ends[1]

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
                              + re.escape(self.surrounding[1]), '#' + tag, file_str, 1)
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
            outfile = self.infile
        elif not outfile_or_revert:
            outfile = self.infile
        else:
            outfile = outfile_or_revert

        file_contents = self._prepare(outfile, revert)

        # if the input is a word file
        if self.temp_file:
            # use pandoc to yield the desired file
            with open(self.temp_file, 'w') as tmp:
                tmp.write(file_contents)
            run(['pandoc', '-f', 'latex', self.temp_file,
                 '-o', outfile, '--reference-doc', self.infile])
            remove(self.temp_file)
        else:
            with open(outfile, 'w') as file:
                file.write(file_contents)
