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

    def _repl(self, match_object):
        label = match_object.group(0)[2:-1]
        ends = match_object.group(0)[0], match_object.group(0)[-1]
        if label in self.contents.keys():
            return ends[0] + self.contents[label] + ends[1]
        else:
            return (ends[0] +
                    srnd(fmt(__main__.__dict__[label]), False) +
                    ends[1])

    def write(self, outfile=None):
        if outfile is None:
            outfile = self.infile.replace('.tex', '_out.tex')

        self.contents[self.current_tag] = '\n'.join(self.tag_contents)

        with open(self.infile) as file:
            file_contents = file.read()
        file_contents = re.sub(r'[\n ]#[a-zA-Z0-9_]+[\n .]',
                               self._repl,
                               file_contents,
                               re.S, re.M)
        with open(outfile, 'w') as file:
            file.write(file_contents)
