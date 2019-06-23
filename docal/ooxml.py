import ast
from test_word import test

DICT = {}

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

# things that are transformed, used for units and such
TRANSFORMED = {
    'degC': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>C</m:t></m:r>',
    'degF': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>F</m:t></m:r>',
    'deg': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup>'
}

MATH_ACCENTS = {
    'hat': '.',
    'check': '',
    'breve': '',
    'acute': '',
    'grave': '',
    'tilde': ' ̃',
    'bar': ' ̅',
    'vec': 'foo',
    'dot': '',
    'ddot': '',
    'dddot': '',
}

PRIMES = {'prime': "'", '2prime': "''", '3prime': "'''"}


class WordVisitor(ast.NodeVisitor):
    txt = '<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:eastAsiaTheme="minorEastAsia" w:hAnsi="Cambria Math"/></w:rPr><m:t xml:space="preserve">{}</m:t></m:r>'
    txt_rom = '<m:r><m:rPr><m:nor/></m:rPr><w:rPr><w:rFonts w:ascii="Cambria Math" w:eastAsiaTheme="minorEastAsia" w:hAnsi="Cambria Math"/></w:rPr><m:t xml:space="preserve">{}</m:t></m:r>'
    sub = '<m:sSub><m:e>{}</m:e><m:sub>{}</m:sub></m:sSub>'
    sup = '<m:sSup><m:e>{}</m:e><m:sup>{}</m:sup></m:sSup>'
    parend = '<m:d><m:e>{}</m:e></m:d>'
    acc = '<m:acc><m:accPr><m:chr m:val="{}"/></m:accPr><m:e>{}</m:e></m:acc>'
    rad = '<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{}</m:e></m:rad>'
    summation = '<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr><m:sub><m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr><m:t>i=1</m:t></m:r></m:sub><m:sup><m:r><m:t>{}</m:t></m:r></m:sup><m:e>{}</m:e></m:nary>'
    func_name = '<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>{}</m:t></m:r>'
    func = '<m:func><m:fName>{}</m:fName><m:e>{}</m:e></m:func>'
    frac = '<m:f><m:num>{}</m:num><m:den>{}</m:den></m:f>'

    def __init__(self, mul_symbol, div_symbol, subs, mat_size, working_dict=DICT):
        self.mul_symbol = mul_symbol
        self.div_symbol = div_symbol
        self.subs = subs
        self.mat_size = mat_size
        self.dict = working_dict

    def format_name(self, name_str: str) -> str:
        '''
        Turn a variable name into a ooxml term that has sub/superscripts, accents,
        upright if needed, and prime signs
        '''
        parts = name_str.strip(' _').split('_')
        parts_final = parts[:]
        accent_locations = []
        for index, part in enumerate(parts):
            # no modification is wanted if the first character is 0
            if part.startswith('0') and len(part) > 1:
                parts_final[index] = self.txt_rom.format(part[1:])
            # convert to greek letters
            elif part in GREEK_LETTERS:
                parts_final[index] = self.txt.format(GREEK_LETTERS[part])
            # maybe if it is something that is simpler to write than its value
            elif part in TRANSFORMED:
                parts_final[index] = TRANSFORMED[part]
            # convert primes
            elif part in MATH_ACCENTS:
                # (to choose which to surround)
                which = index - 2 if not parts[index - 1] else index - 1
                parts_final[which] = self.acc.format(MATH_ACCENTS[part], parts_final[which])
                accent_locations.append(index)
            elif part in PRIMES.keys():
                which = index - 2 if not parts[index - 1] else index - 1
                parts_final[which] = self.sup.format(parts_final[which], self.txt.format(PRIMES[part]))
                accent_locations.append(index)
            # change in ... as [Dd]elta...
            elif part.startswith('Delta') or part.startswith('delta'):
                delta, var = part[:len('delta')], part[len('delta'):]
                parts_final[index] = self.txt.format(GREEK_LETTERS[delta]) + self.format_name(var)
            elif part:
                parts_final[index] = self.txt_rom.format(part) if len(part) > 1 else self.txt.format(part)
        # remove the accents
        parts_final = [part for index, part in enumerate(parts_final)
                       if index not in accent_locations]
        parts_final = [part.split('_') for part in '_'.join(parts_final).split('__')]
        parts_final = [self.sub.format(p[0], p[1]) if len(p) > 1 else p[0] for p in parts_final]
        name = self.sup.format(parts_final[0], parts_final[1]) if len(parts_final) > 1 else parts_final[0]

        return name

    def prec(self, n):
        return getattr(self, 'prec_'+n.__class__.__name__, getattr(self, 'generic_prec'))(n)

    def visit_Expr(self, n):
        return f'<w:p><m:oMathPara><m:oMath>{self.visit(n.value)}</m:oMath></m:oMathPara></w:p>'

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
                return _prep4lx(eval(f'{base}.{attr}', self.dict), self.mat_size).value
            # get, prep and visit the value
            return self.visit(_prep4lx(eval(f'{base}.{attr}', self.dict), self.mat_size))
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
        args = self.txt.format(', ').join([self.visit(arg) for arg in n.args])
        ignored = ['round', 'matrix', 'Matrix', 'array', 'ndarray']
        if func == 'sqrt':
            return self.rad.format(args)
        elif func == 'inv':
            return self.sup.format(args, -1)
        elif func == 'transpose':
            return self.sup.format(args, 'T')
        elif func == 'sum':
            if isinstance(n.args[0], ast.Name):
                n.args[0] = self.visit_Name(n.args[0], True)
            if isinstance(n.args[0], ast.List) or isinstance(n.args[0], ast.Tuple):
                return self.summation.format(len(n.args[0].elts), args)
            else:
                return self.txt.format('∑') + self.parend.format(args)
        elif func == 'log':
            return self.func.format(self.func_name.format('ln'), args)
        elif func == 'log10':
            return self.func.format(self.func_name.format('log'), args)
        elif func == 'log2':
            return self.func.format(self.sub.format(self.func_name.format('log'), self.txt.format(2)), args)
        elif func in ignored:
            return self.visit(n.args[0])
        return self.txt_rom.format(func) + self.parend.format(args)

    def prec_Call(self, n):
        return 1000

    # variables
    def visit_Name(self, n, shallow=False):
        if self.subs:
            # substitute the value of the variable by formatted value
            try:
                # if the raw ast object is needed (for BinOp)
                if shallow:
                    return _prep4lx(self.dict[n.id], self.mat_size).value
                # to prevent infinite recursion:
                if str(self.dict[n.id]) == n.id:
                    return self.format_name(str(self.dict[n.id]))
                qty = self.visit(_prep4lx(self.dict[n.id], self.mat_size))
                unit = fr'\, \mathrm{{{latexify(self.dict[n.id + UNIT_PF], div_symbol="/")}}}' \
                    if n.id + UNIT_PF in self.dict.keys() and self.dict[n.id + UNIT_PF] \
                    and self.dict[n.id + UNIT_PF] != '_' else ''
                # if the quantity is raised to some power and has a unit,
                # surround it with PARENS
                if hasattr(n, 'is_in_power') and n.is_in_power and unit and unit != '_':
                    return f'\\left({qty} {unit}\\right)'
                return qty + unit
            except KeyError:
                log.warning('The variable %s has not been defined.', n.id)
        return self.format_name(n.id)

    def prec_Name(self, n):
        return 1000

    def visit_Num(self, n):
        number = n.n
        if number != 0 and (abs(number) > 1000 or abs(number) < 0.1):
            # in scientific notation
            num_ls = f'{number:.2E}'.split('E')
            # remove the preceding zeros and + in the powers like +07 to just 7
            num_ls[1] = num_ls[1][0].lstrip('+') + num_ls[1][1:].lstrip('0')
            # make them appear as powers of 10
            return self.txt.format(num_ls[0]) + self.parend.format(self.sup.format(self.txt.format(10), self.txt.format(num_ls[1])))
        if number == int(number):
            return self.txt.format(int(number))
        return self.txt.format(round(number, 2))

    def prec_Num(self, n):
        if hasattr(n, 'is_in_power') and n.is_in_power \
                and n.n != 0 and (abs(n.n) > 1000 or abs(n.n) < 0.1):
            return 300
        return 1000

    def visit_UnaryOp(self, n):
        if isinstance(n.op, ast.USub):
            n.operand.is_in_unaryop = True
        if self.prec(n.op) >= self.prec(n.operand) \
                or (hasattr(n, 'is_in_unaryop') and n.is_in_unaryop):
            return self.txt.format(self.visit(n.op)) + self.parend.format(self.visit(n.operand))
        else:
            return self.txt.format(self.visit(n.op)) + self.visit(n.operand)

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

        div_and_frac = self.div_symbol == 'frac' and isinstance(n.op, ast.Div)
        if self.prec(n.op) > self.prec(n.left) and not div_and_frac:
            left = self.parend.format(self.visit(n.left))
        else:
            left = self.visit(n.left)
        if self.prec(n.op) > self.prec(tmp_right) and \
                not isinstance(n.op, ast.Pow) and not div_and_frac:
            # not forgetting the units, so n.right
            left = self.parend.format(self.visit(n.right))
        else:
            right = self.visit(n.right)
        if isinstance(n.op, ast.Mult):
            # unless the right term is a Num or BinOp whose operation is power
            no_need = not any([isinstance(tmp_right, ast.BinOp)
                               and isinstance(tmp_right.op, ast.Pow)
                               and isinstance(tmp_right.left, ast.Num),
                               isinstance(tmp_right, ast.Num)])
            if no_need:
                return left + self.txt.format(' ') + right
        elif self.div_symbol == 'frac':
            if isinstance(n.op, ast.Div):
                return self.frac.format(left, right)
            elif isinstance(n.op, ast.FloorDiv):
                return self.frac.format(left, right)
        return left + self.txt.format(self.visit(n.op)) + right

    def prec_BinOp(self, n):
        return self.prec(n.op)

    def visit_Sub(self, n):
        return '-'

    def prec_Sub(self, n):
        return 300

    def visit_Add(self, n):
        return '+'

    def prec_Add(self, n):
        return 300

    def visit_Mult(self, n):
        if self.mul_symbol == '*':
            return '×'
        elif self.mul_symbol == '.':
            return '⋅'
        return ''

    def prec_Mult(self, n):
        return 400

    def visit_Div(self, n):
        if self.div_symbol == '/':
            return '/'
        else:
            return '÷'

    def prec_Div(self, n):
        return 400

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
        return 0

def wordify(expr):
    tr = ast.parse(expr)
    t = WordVisitor('*', 'frac', False, 5).visit(tr.body[0])
    return t

test(wordify('-348*56/45*sqrt(2*alpha)'))
