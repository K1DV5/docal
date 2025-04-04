from os import path
import re
import logging
from ..processing import PATTERN

logger = logging.getLogger(__name__)

DEFAULT_FILE = 'Untitled.tex'

# surrounding of the content sent for reversing (something that doesn't
# change the actual content of the document, and works inside lines)
SURROUNDING = ['{} {{ {}', '{} }} {}']

GREEK_LETTERS = ['alpha',
                 'nu',
                 'beta',
                 'xi',
                 'Xi',
                 'gamma',
                 'Gamma',
                 'delta',
                 'Delta',
                 'pi',
                 'Pi',
                 'epsilon',
                 'varepsilon',
                 'rho',
                 'varrho',
                 'zeta',
                 'sigma',
                 'Sigma',
                 'eta',
                 'tau',
                 'theta',
                 'vartheta',
                 'Theta',
                 'upsilon',
                 'Upsilon',
                 'iota',
                 'phi',
                 'varphi',
                 'Phi',
                 'kappa',
                 'chi',
                 'lambda',
                 'Lambda',
                 'psi',
                 'Psi',
                 'mu',
                 'omega',
                 'Omega',
                 ]

MATH_ACCENTS = ['hat',
                'check',
                'breve',
                'acute',
                'grave',
                'tilde',
                'bar',
                'vec',
                'dot',
                'ddot',
                'dddot',
                ]

PRIMES = {'prime': "'", '2prime': "''", '3prime': "'''"}

class syntax:

    transformed = {
    'degC': '\\,^\\circ \\mathrm{C}',
    'degF': '\\,^\\circ \\mathrm{F}',
    'deg': '\\,^\\circ',
    'integral': '\\int '
    }

    minus = '-'
    times = r'\times '
    div = r'\div '
    cdot = r'\cdot '
    halfsp = r'\,'
    neg = '\\neg'
    gt = '>'
    lt = '<'
    gte = '\\geq'
    lte = '\\leq'
    cdots = '\\cdots'
    vdots = '\\vdots'
    ddots = '\\ddots'

    greek_letters = GREEK_LETTERS
    math_accents = MATH_ACCENTS
    primes = PRIMES

    def txt(self, text):
        return text

    def txt_rom(self, text):
        return fr'\mathrm{{{text}}}'

    def txt_math(self, text):
        return f'\\text{{{text}}}'

    def sub(self, base, s): 
        return fr'{{{base}}}_{{{s}}}'

    def sup(self, base, s):
        return f'{{{base}}}^{{{s}}}'

    def acc(self, base, accent):
        return f'{{{base}}}{accent}'

    def rad(self, base):
        return fr'\sqrt{{{base}}}'

    def summation(self, base, end):
        return fr'\sum_{{i=1}}^{{{end}}} {{{base}}}'

    def func_name(self, name):
        return fr'\operatorname{{{name}}}'

    def frac(self, num, den):
        return fr'\frac{{{num}}}{{{den}}}'

    def math_disp(self, math):
        return f'\\[\n{math}\n\\]'

    def math_inln(self, math):
        return f'\\(\\displaystyle {math}\\)'

    def greek(self, name):
        return '\\' + name

    def accent(self, acc, base):
        return fr'\{acc}{{{base}}}'

    def prime(self, base, prime):
        return f'{{{base}}}{PRIMES[prime]}'

    def delmtd(self, contained, kind=0):
        kinds = ['()', '[]', '{}', ('\\lfloor', '\\rfloor')]
        return f'\\left{kinds[kind][0]}{contained}\\right{kinds[kind][1]}'

    def matrix(self, elmts, full=False):
        if full:  # top level, full matrix
            m_form = '\\begin{{matrix}}\n{}\n\\end{{matrix}}'
            rows = '\\\\\n'.join(elmts)
            return self.delmtd(m_form.format(rows), 1)
        return ' & '.join(elmts)

    def eqarray(self, eqns: list):
        srnds = ['\\begin{aligned}\n', '\n\\end{aligned}']
        inner = '\\\\\n'.join([' &= '.join(eq_ls) for eq_ls in eqns])
        return srnds[0] + inner + srnds[1]


class document:
    '''handles the latex files'''

    # warning for tag place protection in document:
    warning = ('BELOW IS AN AUTO GENERATED LIST OF TAGS. '
               'DO NOT DELETE IT IF REVERSING IS DESIRED!!!\n%')

    def __init__(self, infile=None, outfile=None):

        # the tag pattern
        self.pattern = PATTERN
        if infile:
            self.infile = infile
            with open(self.infile, encoding='utf-8') as file:
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
                         for tag in self.pattern.finditer(self.file_contents)]
        else:
            self.file_contents = '\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n%s\n\\end{document}' 
            self.infile = self.tagline = self.tags = None
        if outfile is None:
            self.outfile = self.infile if self.infile else DEFAULT_FILE
        else:
            self.outfile = path.abspath(outfile)
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
                              '#' + tag, file_str, count=1)
        # for inplace editing
        self.file_contents = file_str
        return file_str

    def _subs_in_place(self, values: dict):
        file_str = self.file_contents + f'\n\n% {self.warning} [['
        file_str = self.pattern.sub(lambda x: self._repl(x, True, values),
                               file_str)
        for tag in self.calc_tags:
            file_str += tag + ' '
        file_str = file_str.rstrip('\n') + ']]'
        return file_str

    def _subs_separate(self, values: dict):
        return self.pattern.sub(lambda x: self._repl(x, False, values),
                           self.file_contents)

    def _repl(self, match_object, surround: bool, values: dict):
        start, tag, end = [m if m else '' for m in match_object.groups()]
        if tag in values:
            result = '\n'.join([val[1] for val in values[tag]])
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

    def write(self, values={}):
        if len(values):
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
                self.file_contents = self.file_contents % '\n'.join([
                    '\n'.join([v[1] for v in val]) for val in values.values()
                ])

        logger.info('[writing file] %s', self.outfile)
        with open(self.outfile, 'w', encoding='utf-8') as file:
            file.write(self.file_contents)

