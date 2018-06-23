from shutil import rmtree
import __main__
import scpycalc as sc

class document:
    '''contains (almost) all of the functionality for a LaTeX document'''

    def __init__(self):
        '''begins writing a document with a default documentclass: article, 11pt
        Note: chapter cannot be used with article'''
        self.name = __main__.__file__.replace('.py', '')
        self.type = 'article'
        self.options = '11pt'
        self.preamble = ''
        self.content = ''
        self.file = 'tex'
        exec('from sympy.physics.units import meter, second, kilogram',
             __main__.__dict__)

    def __enter__(self):
        return self

    def append(self, content, ws=2):
        self.content += '\n' * ws + content

    def chapter(self, title):
        self.append(f'\n\\chapter{{{title}}}', 1)

    def section(self, title):
        self.append(f'\n\\section{{{title}}}', 1)

    def subsection(self, title):
        self.append(f'\n\\subsection{{{title}}}', 1)

    def subsubsection(self, title):
        self.append(f'\n\\subsubsection{{{title}}}', 1)

    def equation(self, *eqns, inline: bool = False, raw: bool = False):
        sc.equation(*eqns, inline, raw)

    def aserar(self, eqn, intent='full', unit=None):
        sc.aserar(eqn, intent, unit)

    def solve(self, strg, var):
        sc.solve(strg, var)

    def figure(self, fig, label='', caption=''):
        if label == '':
            label = fig.split('.')[0]
        if caption != '':
            self.append('\\begin{figure}'
                        '\n\\centering\n\\includegraphics{'
                        f'{fig}'
                        '}\n\\caption{'
                        f'{caption}'
                        '}\n\\label{'
                        f'{label}'
                        '}\n\\end{figure}')
        else:
            self.append('\\includegraphics{' + fig + '}')

    def __exit__(self, *args):
        # equation handling package
        if '\\begin{align}' in self.content or '\\begin{matrix}' in self.content:
            self.preamble += '\n\\usepackage{amsmath}'
        # figures handling package
        if '\\includegraphics{' in self.content:
            self.preamble += '\n\\usepackage{graphicx}'
        post_fixes = {'_{}': '',
                      '\\mathrm{m \\, N}': '\\mathrm{N \\, m}',
                      '^{1.0}': ''}
        for wrng, rght in post_fixes.items():
            self.content = self.content.replace(wrng, rght)
        self.content = ('\\documentclass['
                        f'{self.options}]{{'
                        f'{self.type}}}\n'
                        f'{self.preamble}'
                        '\n\\begin{document}'
                        f"{self.content}"
                        '\n\n\\end{document}')
        with open(self.name + '.tex', 'w') as file:
            file.write(self.content)
        rmtree('__pycache__', ignore_errors=True)
        if self.file != 'tex':
            from subprocess import run
            run(['pandoc', self.name + '.tex', '-o', self.name + '.' + self.file])
        print('Document Written Successfully!')
