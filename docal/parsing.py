# -ipy
'''
python expression to latex converter with import prefixes removal and optional
substitution of values from the main script, based on Geoff Reedy's answer to
https://stackoverflow.com/questions/3867028/converting-a-python-numeric-expression-to-latex
'''

import ast
import re
import logging
from .document import DICT

log = logging.getLogger(__name__)

# the tag pattern
PATTERN = re.compile(r'(?s)([^\w\\]|^)#(\w+?)(\W|$)')

# what will be appended after the names to store units for those names
UNIT_PF = '___0UNIT0'

DEFAULT_MAT_SIZE = 10

GREEK_LETTERS = {
    'alpha':      'α',
    'nu':         'ν',
    'beta':       'β',
    'xi':         'ξ',
    'Xi':         'Ξ',
    'gamma':      'γ',
    'Gamma':      'Γ',
    'delta':      'δ',
    'Delta':      '∆',
    'pi':         'π',
    'Pi':         'Π',
    'epsilon':    'ϵ',
    'varepsilon': 'ε',
    'rho':        'ρ',
    'varrho':     'ϱ',
    'zeta':       'ζ',
    'sigma':      'σ',
    'Sigma':      'Σ',
    'eta':        'η',
    'tau':        'τ',
    'theta':      'θ',
    'vartheta':   'ϑ',
    'Theta':      'Θ',
    'upsilon':    'υ',
    'Upsilon':    'Υ',
    'iota':       'ι',
    'phi':        'φ',
    'varphi':     'ϕ',
    'Phi':        'Φ',
    'kappa':      'κ',
    'chi':        'χ',
    'lambda':     'λ',
    'Lambda':     'Λ',
    'psi':        'ψ',
    'Psi':        'Ψ',
    'mu':         'µ',
    'omega':      'ω',
    'Omega':      'Ω',
    }

MATH_ACCENTS = {
    'hat': '&#x0302;',
    'check': '&#x030C;',
    'breve': '&#x02D8;',
    'acute': '&#x0301;',
    'grave': '&#x0300;',
    'tilde': '&#x0303;',
    'bar': '&#x0304;',
    'vec': '&#x20D7;',
    'dot': '&#x0307;',
    'ddot': '&#x0308;',
    'dddot': '&#x20DB;',
    }

PRIMES = {'prime': "'", '2prime': "''", '3prime': "'''"}

class SyntaxWord:

    # common string blocks (can be formatted)
    txt = '<m:r><m:t xml:space="preserve">{}</m:t></m:r>'
    txt_rom = '<m:r><m:rPr><m:nor/></m:rPr><w:rPr><w:rFonts w:ascii="Cambria Math" w:eastAsiaTheme="minorEastAsia" w:hAnsi="Cambria Math"/></w:rPr><m:t xml:space="preserve">{}</m:t></m:r>'
    txt_math = txt_rom
    sub = '<m:sSub><m:e>{}</m:e><m:sub>{}</m:sub></m:sSub>'
    sup = '<m:sSup><m:e>{}</m:e><m:sup>{}</m:sup></m:sSup>'
    acc = '<m:acc><m:accPr><m:chr m:val="{}"/></m:accPr><m:e>{}</m:e></m:acc>'
    rad = '<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{}</m:e></m:rad>'
    summation = '<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr><m:sub><m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr><m:t>i=1</m:t></m:r></m:sub><m:sup><m:r><m:t>{}</m:t></m:r></m:sup><m:e>{}</m:e></m:nary>'
    func_name = '<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>{}</m:t></m:r>'
    func = '<m:func><m:fName>{}</m:fName><m:e>{}</m:e></m:func>'
    frac = '<m:f><m:num>{}</m:num><m:den>{}</m:den></m:f>'
    math_disp = '<m:oMathPara><m:oMath>{}</m:oMath></m:oMathPara>'
    math_inln = '<m:oMath>{}</m:oMath>'

    # things that are transformed, used for units and such
    transformed = {
        'degC': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>C</m:t></m:r>',
        'degF': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>F</m:t></m:r>',
        'deg': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup>'
    }

    # some symbols
    times = '×'
    div = '÷'
    cdot = '⋅'
    halfsp = '&#8239;'
    neg = '¬'
    gt = '&gt;'
    lt = '&lt;'
    gte = '&ge;'
    lte = '&le;'
    cdots = '⋯'
    vdots = '⋮'
    ddots = '⋱'

    # things that can't be accomplished with formatting strings
    def greek(self, name):
        return self.txt.format(GREEK_LETTERS[name])

    def accent(self, acc, base):
        return self.acc.format(MATH_ACCENTS[acc], base)

    def prime(self, base, prime):
        return self.sup.format(base, self.txt.format(PRIMES[prime]))

    def delmtd(self, contained, kind=0):
        surround = '<m:dPr><m:begChr m:val="{}"/><m:endChr m:val="{}"/></m:dPr>'
        kinds = ['[]', '{}', '⌊⌋']
        form = '<m:d>{}<m:e>{}</m:e></m:d>'
        if kind == 0:
            return form.format('', contained)
        return form.format(surround.format(kinds[kind-1][0], kinds[kind-1][1]), contained)

    def matrix(self, elmts, full=False):
        if full:  # top level, full matrix
            m_form = '<m:m>{}</m:m>'
            rows = ''.join([f'<m:mr><m:e>{e}</m:e></m:mr>' for e in elmts])
            return self.delmtd(m_form.format(rows), 1)
        return '</m:e><m:e>'.join(elmts)

    def eqarray(self, eqns: list):
        form = '<m:eqArr>{}</m:eqArr>'
        line_form = '<m:e>{}</m:e>'
        align_chr = self.txt.format('&amp;=')
        return form.format(''.join([line_form.format(align_chr.join(eq)) for eq in eqns]))


class SyntaxLatex:
    txt = '{}'
    txt_rom = r'\mathrm{{{}}}'
    txt_math = '\\text{{{}}}'
    sub = r'{{{}}}_{{{}}}'
    sup = '{{{}}}^{{{}}}'
    acc = '{{{}}}{}'
    rad = r'\sqrt{{{}}}'
    summation = r'\sum_{{i=1}}^{{{}}} {{{}}}'
    func_name = r'\operatorname{{{}}}'
    func = '{{{}}} {{{}}}'
    frac = r'\frac{{{}}}{{{}}}'
    math_disp = '\\[\n{}\n\\]'
    math_inln = '\\(\\displaystyle {}\\)'

    transformed = {
    'degC': '\\,^\\circ \\mathrm{C}',
    'degF': '\\,^\\circ \\mathrm{F}',
    'deg': '\\,^\\circ'
    }

    times = r'\times '
    div = r'\div '
    cdot = r'\cdot '
    halfsp = r'\,'
    neg = '\\neg'
    gt = '>'
    lt = '<'
    gte = '>='
    lte = '<='
    cdots = '\\cdots'
    vdots = '\\vdots'
    ddots = '\\ddots'

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


# syntax selector
def select_syntax(typ):
    if typ == 'word':
        return SyntaxWord()
    else:
        return SyntaxLatex()


def _parens_balanced(expr: str) -> bool:
    '''
    check if the pairs that must be balanced are actually balanced
    '''
    # those that must be matched in equations
    parens = ['()', '[]', '{}']

    return all([expr.count(p[0]) == expr.count(p[1]) for p in parens])


def _split(what: str, char='=', count=None, last=True) -> list:
    '''split a given equation at the main equal signs and not at the ones
    used for other purposes like giving a kwarg'''

    balanced = []
    incomplete = ''
    for e in what.split(char):
        e = e.strip()
        if incomplete or not _parens_balanced(e):
            incomplete += (char if incomplete else '') + e
            if incomplete and _parens_balanced(incomplete):
                balanced.append(incomplete)
                incomplete = ''
        else:
            balanced.append(e)
    if incomplete:
        raise SyntaxError('The number of parens is not balanced.')
    if not count and len(balanced) > 1:
        if last:
            # if splitting only at the last = is wanted, join the others
            balanced = [char.join(balanced[:-1]), balanced[-1]]
        elif last is not None:
            balanced = [balanced[0], char.join(balanced[1:])]

    return balanced


def _prep4lx(quantity, syn_obj, mat_size=(DEFAULT_MAT_SIZE, DEFAULT_MAT_SIZE)):
    '''
    parse the given quantity to an AST object so it can be integrated in _LatexVisitor
    '''

    quantity_type = str(type(quantity))
    ndquantities = ['array', 'Array', 'matrix', 'Matrix', 'list']

    if any([typ in quantity_type for typ in ndquantities]):
        if isinstance(mat_size, int):
            mat_size = (mat_size, mat_size)

        quantity = _fit_matrix(quantity, syn_obj, mat_size)

    return ast.parse(str(quantity)).body[0]


def _fit_array(array, syn_obj, mat_size=DEFAULT_MAT_SIZE):
    '''
    shorten the given 1 dimensional matrix/array by substituting ellipsis (...)
    '''

    if len(array) > mat_size:
        array = [*array[:mat_size - 2], syn_obj.vdots, array[-1]]

    return array


def _fit_big_matrix(matrix, syn_obj, size):
    '''
    shrink a big matrix by substituting vertical, horizontal and diagonal ...
    '''

    rows, cols = size
    mat = matrix[:rows - 2, :cols - 2].tolist()
    last_col = matrix[:rows - 2, -1].tolist()
    if not isinstance(last_col[0], list):
        last_col = [[e] for e in last_col]
    last_row = matrix[-1, :cols - 2].tolist()
    if not isinstance(last_row[0], list):
        last_row = [[e] for e in last_row]
    last_element = matrix[-1, -1]
    for index, element in enumerate(mat):
        element += [syn_obj.cdots, last_col[index][0]]
    mat.append([syn_obj.vdots] * (cols - 2) + [syn_obj.ddots, syn_obj.vdots])
    mat.append(last_row[0] + [syn_obj.cdots, last_element])

    return mat


def _fit_wide_matrix(matrix, syn_obj, max_cols):
    '''
    make the wide matrix narrower by substituting horizontal ... in the rows
    '''

    mat = matrix[:, :max_cols - 2].tolist()
    last_col = matrix[:, -1].tolist()
    for index, element in enumerate(mat):
        element += [syn_obj.cdots, last_col[index][0]]

    return mat


def _fit_long_matrix(matrix, syn_obj, max_rows):
    '''
    shorten the matrix by substituting vertical ... in the columns
    '''

    mat = matrix[:max_rows - 2, :].tolist()
    mat += [[syn_obj.vdots] * matrix.shape[1]]
    mat += matrix[-1, :].tolist()

    return mat


def _fit_matrix(matrix, syn_obj, max_size=(DEFAULT_MAT_SIZE, DEFAULT_MAT_SIZE)):
    '''
    if there is a need, make the given matrix smaller
    '''

    shape = (len(matrix),) if isinstance(matrix, list) else matrix.shape
    # array -> short
    if len(shape) == 1 and shape[0] > max_size[0] or isinstance(matrix, list):
        mat_ls = _fit_array(matrix, syn_obj, max_size[0])
    # too big -> small
    elif matrix.shape[0] > max_size[0] and matrix.shape[1] > max_size[1]:
        mat_ls = _fit_big_matrix(matrix, syn_obj, max_size)
    # too long -> small
    elif matrix.shape[0] > max_size[0] and matrix.shape[1] < max_size[1]:
        mat_ls = _fit_long_matrix(matrix, syn_obj, max_size[0])
    # too wide -> small
    elif matrix.shape[0] < max_size[0] and matrix.shape[1] > max_size[1]:
        mat_ls = _fit_wide_matrix(matrix, syn_obj, max_size[1])
    # already small so :)
    else:
        mat_ls = matrix.tolist()

    return mat_ls


class MathVisitor(ast.NodeVisitor):

    def __init__(self, mul, div, subs, mat_size, decimal=3, working_dict=DICT, typ='latex', ital=True):
        self.mul = mul
        self.div = div
        self.subs = subs
        self.mat_size = mat_size
        self.decimal = int(decimal)
        self.dict = working_dict
        self.s = select_syntax(typ)
        self.ital = ital

    def format_name(self, name_str: str) -> str:
        '''
        Turn a variable name into a supported syntax term that has
        sub/superscripts, accents, upright if needed, and prime signs
        '''
        parts = name_str.strip(' _').split('_')
        parts_final = parts[:]
        accent_locations = []
        for index, part in enumerate(parts):
            # no modification is wanted if the first character is 0
            if part.startswith('0') and len(part) > 1:
                parts_final[index] = self.s.txt_rom.format(part[1:])
            # convert to greek letters
            elif part in GREEK_LETTERS:
                parts_final[index] = self.s.greek(part)
            # maybe if it is something that is simpler to write than its value
            elif part in self.s.transformed:
                parts_final[index] = self.s.transformed[part]
            # convert primes
            elif part in MATH_ACCENTS:
                # (to choose which to surround)
                which = index - 2 if not parts[index - 1] else index - 1
                parts_final[which] = self.s.accent(part, parts_final[which])
                accent_locations.append(index)
            elif part in PRIMES.keys():
                which = index - 2 if not parts[index - 1] else index - 1
                parts_final[which] =  self.s.prime(parts_final[which], part)
                accent_locations.append(index)
            # change in ... as [Dd]elta...
            elif part.startswith('Delta') or part.startswith('delta'):
                delta, var = part[:len('delta')], part[len('delta'):]
                parts_final[index] = self.s.greek(delta) + self.s.txt.format(' ') + self.format_name(var)
            elif len(part) > 1 or not self.ital:
                parts_final[index] = self.s.txt_rom.format(part)
            elif part:
                parts_final[index] = self.s.txt.format(part)
        # remove the accents
        parts_final = [part for index, part in enumerate(parts_final)
                       if index not in accent_locations]
        parts_final = [part.split('_') for part in '_'.join(parts_final).split('__')]
        parts_final = [self.s.sub.format(p[0], p[1]) if len(p) > 1 else p[0] for p in parts_final]
        name = self.s.sup.format(parts_final[0], parts_final[1]) if len(parts_final) > 1 else parts_final[0]

        return name

    def prec(self, n):
        return getattr(self, 'prec_'+n.__class__.__name__, getattr(self, 'generic_prec'))(n)

    def visit_Expr(self, n):
        return self.visit(n.value)

    def visit_Assign(self, n):
        return self.s.txt.format('=').join([self.visit(t) for t in n.targets + [n.value]])

    def visit_Compare(self, n):
        collect = [self.visit(n.left)]
        for i, op in enumerate(n.ops):
            collect.append(self.s.txt.format(self.visit(op)))
            collect.append(self.visit(n.comparators[i]))
        return ''.join(collect)

    def visit_Eq(self, n):
        return self.s.txt.format('=')

    def visit_Gt(self, n):
        return self.s.gt

    def visit_Lt(self, n):
        return self.s.lt

    def visit_LtE(self, n):
        return self.s.lte

    def visit_GtE(self, n):
        return self.s.gte

    # attributes (foo.bar)
    def visit_Attribute(self, n, shallow=False):
        # if the value is desired
        if self.subs:
            # if it is a variable take its name
            if isinstance(n.value, ast.Name):
                base = n.value.id
            else:
                # it might be another attribute so visit it on its own and if
                # it is, we want its string representation
                n.value.is_in_attr = True
                base = self.visit(n.value)
            attr = n.attr
            # if it is inside another attribute, return the string representation
            if hasattr(n, 'is_in_attr') and n.is_in_attr:
                return f'{base}.{attr}'
            if shallow:
                return _prep4lx(eval(f'{base}.{attr}', self.dict), self.s, self.mat_size).value
            # get, prep and visit the value
            return self.visit(_prep4lx(eval(f'{base}.{attr}', self.dict), self.s, self.mat_size))
        # only get the part after the dot
        return self.format_name(n.attr)

    def prec_Attribute(self, n):
        return 1000

    # function calls
    def visit_Call(self, n):
        if isinstance(n.func, ast.Attribute):
            func = self.visit(n.func.attr)
        elif isinstance(n.func, ast.Name):
            func = n.func.id
        else:
            func = self.visit(n.func)
        args = self.s.txt.format(', ').join([self.visit(arg) for arg in n.args])
        ignored = ['round', 'matrix', 'Matrix', 'array', 'ndarray']
        if func == 'sqrt':
            return self.s.rad.format(args)
        elif func == 'inv':
            return self.s.sup.format(args, -1)
        elif func == 'transpose':
            return self.s.sup.format(args, 'T')
        elif func == 'sum':
            if isinstance(n.args[0], ast.Name):
                n.args[0] = self.visit_Name(n.args[0], True)
            if isinstance(n.args[0], ast.List) or isinstance(n.args[0], ast.Tuple):
                return self.s.summation.format(len(n.args[0].elts), args)
            else:
                return self.s.txt.format(self.s.greek('Sigma')) + self.s.delmtd(args)
        elif func == 'log10':
            return self.s.func.format(self.s.func_name.format('log'), args)
        elif func == 'log2':
            return self.s.func.format(self.s.sub.format(self.s.func_name.format('log'), self.s.txt.format(2)), args)
        elif func in ignored:
            return self.visit(n.args[0])
        return self.s.txt_rom.format(func) + self.s.delmtd(args)

    def prec_Call(self, n):
        return 1000

    def visit_Lambda(self, n):
        return self.visit(n.body)

    def prec_Lambda(self, n):
        return self.prec(n.body)

    # variables
    def visit_Name(self, n, shallow=False):
        if self.subs:
            # substitute the value of the variable by formatted value
            try:
                # if the raw ast object is needed (for BinOp)
                if shallow:
                    return _prep4lx(self.dict[n.id], self.s, self.mat_size).value
                # to prevent infinite recursion:
                if str(self.dict[n.id]) == n.id:
                    return self.format_name(str(self.dict[n.id]))
                qty = self.visit(_prep4lx(self.dict[n.id], self.s, self.mat_size))
                typ = 'word' if isinstance(self.s, SyntaxWord) else 'latex'
                unit = self.s.txt.format(self.s.halfsp) + \
                    to_math(self.dict[n.id + UNIT_PF], div="/", ital=False, decimal=self.decimal, typ=typ) \
                    if n.id + UNIT_PF in self.dict.keys() and self.dict[n.id + UNIT_PF] \
                    and self.dict[n.id + UNIT_PF] != '_' else ''
                # if the quantity is raised to some power and has a unit,
                # surround it with PARENS
                if hasattr(n, 'is_in_power') and n.is_in_power and unit and unit != '_':
                    return self.s.delmtd(qty + unit)
                return qty + unit
            except KeyError:
                log.warning('The variable %s has not been defined.', n.id)
        return self.format_name(n.id)

    def prec_Name(self, n):
        return 1000

    def visit_Constant(self, n):
        kind = type(n.value)
        if kind in [int, float]:
            n.value = n.value
            if n.value != 0 and (abs(n.value) > 1000 or abs(n.value) < 0.1):
                # in scientific notation
                num_ls = (f'%.{self.decimal}E' % n.value).split('E')
                # num_ls = f'{n.value:.3E}'.split('E')
                # remove the preceding zeros and + in the powers like +07 to just 7
                num_ls[1] = num_ls[1][0].lstrip('+') + num_ls[1][1:].lstrip('0')
                # make them appear as powers of 10
                return self.s.txt.format(num_ls[0]) + self.s.delmtd(self.s.sup.format(self.s.txt.format(10), self.s.txt.format(num_ls[1])))
            if n.value == int(n.value):
                return self.s.txt.format(int(n.value))
            return self.s.txt.format(round(n.value, self.decimal))
        elif kind == str:
            # if whole string contains only word characters
            if re.match(r'\w*', n.value).span()[1] == len(n.value):
                return self.format_name(n.value)
            # or if it seems like an equation
            elif re.search(r'[^=]=[^w]', n.value):
                try:
                    # can't use to_expr because the equations may be
                    # python illegal and latex legal like 3*4 = 5/6
                    return eqn(n.value, srnd=False, vert=False, decimal=self.decimal)
                except SyntaxError:  # if the equation is just beyond understanding
                    pass
            return self.s.txt_math.format(n.value)
        return str(n.value)

    def prec_Constant(self, n):
        if hasattr(n, 'is_in_power') and n.is_in_power \
                and n.n != 0 and (abs(n.n) > 1000 or abs(n.n) < 0.1):
            return 300
        return 1000

    def visit_UnaryOp(self, n):
        if isinstance(n.op, ast.USub):
            n.operand.is_in_unaryop = True
        if self.prec(n.op) >= self.prec(n.operand) \
                or (hasattr(n, 'is_in_unaryop') and n.is_in_unaryop):
            return self.s.txt.format(self.visit(n.op)) + self.s.delmtd(self.visit(n.operand))
        return self.s.txt.format(self.visit(n.op)) + ' ' + self.visit(n.operand)

    def prec_UnaryOp(self, n):
        return self.prec(n.op)

    def visit_BinOp(self, n):
        # to know what the names and attributes contain underneath
        tmp_right = n.right
        if self.subs:
            # shallow visit to know what the name contains (without the units)
            if isinstance(n.right, ast.Name):
                tmp_right = self.visit_Name(n.right, True)
            elif isinstance(n.right, ast.Attribute):
                tmp_right = self.visit_Attribute(n.right, True)
        # to surround with parens if it has units
        if isinstance(n.op, ast.Pow):
            n.left.is_in_power = True
        div_and_frac = self.div == 'frac' and isinstance(n.op, ast.Div)
        if self.prec(n.op) > self.prec(n.left) and not div_and_frac:
            left = self.s.delmtd(self.visit(n.left))
        else:
            left = self.visit(n.left)
        if self.prec(n.op) > self.prec(tmp_right) and \
                not isinstance(n.op, ast.Pow) and not div_and_frac:
            # not forgetting the units, so n.right
            right = self.s.delmtd(self.visit(n.right))
        else:
            right = self.visit(n.right)
        if isinstance(n.op, ast.Mult):
            # unless the right term is a Num or BinOp whose operation is power
            no_need = (not self.mul or self.mul.isspace()) and \
                    not any([isinstance(tmp_right, ast.BinOp)
                             and isinstance(tmp_right.op, ast.Pow)
                             and isinstance(tmp_right.left, ast.Constant),
                             isinstance(tmp_right, ast.Constant)])
            if no_need:
                return left + self.s.txt.format(self.s.halfsp) + right
        elif isinstance(n.op, ast.Pow):
            return self.s.sup.format(left, right)
        elif self.div == 'frac':
            if isinstance(n.op, ast.Div):
                return self.s.frac.format(left, right)
            elif isinstance(n.op, ast.FloorDiv):
                return self.s.delmtd(self.s.frac.format(left, right), 3)
        return left + self.s.txt.format(self.visit(n.op)) + right

    def prec_BinOp(self, n):
        return self.prec(n.op)

    def visit_List(self, n):
        if hasattr(n, 'is_in_list') and n.is_in_list:
            elements = [self.visit(element) for element in n.elts]
            return self.s.matrix(elements)
        for child in ast.iter_child_nodes(n):
            if isinstance(child, ast.List):
                child.is_in_list = True
        elements = [self.visit(element) for element in n.elts]
        return self.s.matrix(elements, True)

    def prec_List(self, n):
        return 1000

    def visit_Tuple(self, n):
        # if it is used as an index for an iterable, add 1 to the elements if
        # they are numbers
        if hasattr(n, 'is_in_index') and n.is_in_index:
            return self.s.txt.format(', ').join([self.s.txt.format(int(i.n) + 1)
                                                 if isinstance(i, ast.Constant)
                                                 else self.visit(i)
                                                 for i in n.elts])
        return self.s.delmtd(self.s.txt.format(', ')
                             .join([self.visit(element) for element in n.elts]))

    def prec_Tuple(self, n):
        return 1000

    # indexed items (item[4:])
    def visit_Subscript(self, n):
        sliced = self.visit(n.value)
        slicer = self.s.delmtd(self.visit(n.slice), 1)
        # if the iterable is kinda not simple, surround it with PARENS
        if isinstance(n.value, ast.BinOp) or isinstance(n.value, ast.UnaryOp):
            return self.s.sub.format(self.s.delmtd(sliced), slicer)
        # write the indices as subscripts
        return self.s.sub.format(sliced, slicer)

    def visit_Index(self, n):
        # this will be used by the tuple visitor
        n.value.is_in_index = True
        # if it is a number, add 1 to it
        if isinstance(n.value, ast.Constant):
            return self.s.txt.format(int(n.value.n) + 1)
        return self.visit(n.value)

    def visit_Slice(self, n):
        # same thing with adding one
        lower, upper = [self.s.txt.format(int(i.n) + 1)
                        if isinstance(i, ast.Constant)
                        else self.visit(i)
                        for i in [n.lower, n.upper]]
        # join the upper and lower limits with -
        return self.visit(lower) + self.s.txt.format('-') + self.visit(upper)

    def visit_ExtSlice(self, n):
        return self.s.txt.format(', ').join([self.visit(s) for s in n.dims])

    def visit_Sub(self, n):
        return '-'

    def prec_Sub(self, n):
        return 300

    def visit_Add(self, n):
        return '+'

    def prec_Add(self, n):
        return 300

    def visit_Mult(self, n):
        if self.mul == '*' or not self.mul or self.mul.isspace():
            return self.s.times
        elif self.mul == '.':
            return self.s.cdot
        return self.s.halfsp

    def prec_Mult(self, n):
        return 400

    def visit_Div(self, n):
        if self.div == '/':
            return '/'
        else:
            return self.s.div

    def prec_Div(self, n):
        return 400

    def prec_FloorDiv(self, n):
        return 400

    def prec_Pow(self, n):
        return 700

    def visit_Mod(self, n):
        return self.s.txt_math.format(' mod ')

    def prec_Mod(self, n):
        return 500

    def visit_LShift(self, n):
        return self.s.func_name('shiftLeft')

    def visit_RShift(self, n):
        return self.s.func_name('shiftRight')

    def visit_BitOr(self, n):
        return self.s.func_name('or')

    def visit_BitXor(self, n):
        return self.s.func_name('xor')

    def visit_BitAnd(self, n):
        return self.s.func_name('and')

    def visit_Invert(self, n):
        return self.s.func_name('invert')

    def prec_Invert(self, n):
        return 800

    def visit_Not(self, n):
        return self.s.neg

    def prec_Not(self, n):
        return 800

    def visit_UAdd(self, n):
        return '+'

    def prec_UAdd(self, n):
        return 800

    def visit_USub(self, n):
        return '-'

    def prec_USub(self, n):
        return 800

    def generic_visit(self, n):
        return str(n)

    def generic_prec(self, n):
        return 1000


def to_math(expr, mul=' ', div='frac', subs=False, mat_size=DEFAULT_MAT_SIZE, decimal=3, working_dict=DICT, typ='latex', ital=True):
    '''
    return the representation of the expr in the appropriate syntax
    '''

    syntax = select_syntax(typ)

    if isinstance(expr, str):
        if expr.strip():
            pt = ast.parse(expr.strip()).body[0]
        else:
            return ''
    else:
        pt = _prep4lx(expr, syntax, mat_size)

    return MathVisitor(mul, div, subs, mat_size, decimal, working_dict, typ, ital).visit(pt)


def build_eqn(eq_list, disp=True, vert=True, typ='latex', srnd=True):
    syntax = select_syntax(typ)
    if len(eq_list) == 1:
        if len(eq_list[0]) == 1:
            inner = eq_list[0][0]
        else:
            inner = syntax.txt.format('=').join(eq_list[0])
    else:
        if vert and disp:
            inner = syntax.eqarray([[syntax.txt.format('=').join(eq[:-1]),
                                     eq[-1]] for eq in eq_list])
        else:
            inner = ''.join([syntax.txt.format('=').join(eq) for eq in eq_list])
    if srnd:
        if disp:
            return syntax.math_disp.format(inner)
        else:
            return syntax.math_inln.format(inner)
    return inner


def eqn(*equation_list, norm=True, disp=True, srnd=True, vert=True, div='frac', mul=' ', decimal=3, typ='latex') -> str:
    '''main api for equations'''

    equals = select_syntax(typ).txt.format('=')

    # split and flatten in case there are any |, and split by =
    equation_list = [_split(eq, last=None) for sub_eq in equation_list for eq in sub_eq.split('|')]

    # prepare the segments of each equation for the syntax object in the form
    # [['x', '5*d'], ['', '5*5'], ['', '25']] (list of lists)
    equations = []
    if norm:
        if len(equation_list) == 1:
            eqns = [to_math(e, mul=mul, div=div, decimal=decimal, typ=typ) for e in equation_list[0]]
            equations.append([equals.join(eqns)])
        else:
            for eq in equation_list:
                # join the first if there are many to align at the last =
                if len(eq) > 1:
                    eq = ['=='.join(eq[:-1]), eq[-1]]
                equations.append([to_math(e, mul=mul, div=div, decimal=decimal, typ=typ) for e in eq])
    else:
        if len(equation_list) == 1:
            equations.append([equals.join(equation_list[0])])
        else:
            for eq in equation_list:
                equations.append([equals.join(eq[:-1]), eq[-1]])

    return build_eqn(equations, disp, vert, typ, srnd)
