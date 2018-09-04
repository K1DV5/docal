# Written by K1DV5
'''
Module document

provides the document class that can be used to
replace the pythontex and pweave requirement.

write your calculations on a separate python file
import this class
use methods tag('tagname') for something like latex labels (placeholders)
in the latex file, and ins(contents) to insert the contents into the tag place.
finally use the write() method to write the final file.
when the python file is run, it writes a tex file with the tags
replaced by contents from the python file.
'''

import re
import __main__
from .calculation import format_quantity as fmt, _surround_equation as srnd

DEFAULT_INFILE = __main__.__file__.replace('.py', '.tex')
WARNING = 'DO NOT DELETE THIS LINE!!!'  # warning for tag place protection


class document:
    '''contains the document handle'''

    def __init__(self, infile=DEFAULT_INFILE):
        self.infile = infile
        self.contents = {}
        self.tag_contents = []
        self.current_tag = 'init'

    def tag(self, tag_name):
        '''insert the current tag and contents into contents,
        reset the tag contents and start a new tag with new name'''

        self.contents[self.current_tag] = '\n'.join(self.tag_contents)
        self.tag_contents.clear()
        self.current_tag = tag_name

    def ins(self, chunk_content):
        self.tag_contents.append(str(chunk_content))

    def _repl(self, match_object, surround: bool):
        label = match_object.group(0)[2:-1]
        ends = match_object.group(0)[0], match_object.group(0)[-1]
        if label in self.contents.keys():
            result = self.contents[label]
        else:
            result = srnd(fmt(__main__.__dict__[label]), False)

        if surround:
            start = ends[0] if ends[0] == '\n' else ''
            end = ends[1] if ends[1] == '\n' else ''
            return ends[0] + '{{{' + start + result + end + '}}}' + ends[1]

        return ends[0] + result + ends[1]

    def _repl_surround(self, match_object):
        return self._repl(match_object, True)

    def _repl_bare(self, match_object):
        return self._repl(match_object, False)

    def _revert_to_tags(self, file_str, tagline):
        start = tagline.group(0).find('[[') + 2
        end = tagline.group(0).rfind(']]')
        taglist = tagline.group(0)[start:end].split()
        file_str = (file_str[:tagline.start()].rstrip('\n') +
                    file_str[tagline.end():])
        for tag in taglist:
            file_str = re.sub(r'(?s){{{.*?}}}', '#' + tag, file_str, 1)
        return file_str

    def _subs_in_place(self, file_str):
        file_str += f'\n\n% {WARNING} [['
        for tag in re.findall(r'(?s)[\n ]#[a-zA-Z0-9_]+[\n .,]', file_str):
            file_str += tag[2:-1] + ' '
        file_str = re.sub(r'(?s)[\n ]#[a-zA-Z0-9_]+[\n .,]',
                          self._repl_surround,
                          file_str)
        file_str = file_str.rstrip('\n') + ']]'
        return file_str

    def _subs_sep(self, file_str):
        return re.sub(r'(?s)[\n ]#[a-zA-Z0-9_]+[\n .,]',
                      self._repl_bare,
                      file_str)

    def write(self, outfile=None):
        self.contents[self.current_tag] = '\n'.join(self.tag_contents)

        with open(self.infile) as file:
            file_contents = file.read()
        tagline = re.search(fr'\n% {WARNING} [\[[a-zA-Z0-9_ ]+\]\]',
                            file_contents)

        if outfile and outfile != self.infile:
            if tagline:
                file_contents = self._revert_to_tags(file_contents, tagline)
                file_contents = self._subs_sep(file_contents)
            else:
                file_contents = self._subs_sep(file_contents)

        else:
            if tagline:
                file_contents = self._revert_to_tags(file_contents, tagline)
            else:
                file_contents = self._subs_in_place(file_contents)

        if not outfile:
            outfile = self.infile

        with open(outfile, 'w') as file:
            file.write(file_contents)
