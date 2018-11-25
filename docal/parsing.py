# -ipy
# -pdb
'''
python expression to latex converter with import prefixes removal and optional
substitution of values from the main script, based on Geoff Reedy's answer to
https://stackoverflow.com/questions/3867028/converting-a-python-numeric-expression-to-latex
'''

import ast

GREEK_LETTERS = [
    'alpha', 'nu', 'beta', 'xi', 'Xi', 'gamma', 'Gamma', 'delta', 'Delta',
    'pi', 'Pi', 'epsilon', 'varepsilon', 'rho', 'varrho', 'zeta', 'sigma',
    'Sigma', 'eta', 'tau', 'theta', 'vartheta', 'Theta', 'upsilon', 'Upsilon',
    'iota', 'phi', 'varphi', 'Phi', 'kappa', 'chi', 'lambda', 'Lambda', 'psi',
    'Psi', 'mu', 'omega', 'Omega'
]

MATH_ACCENTS = [
    'hat', 'check', 'breve', 'acute', 'grave', 'tilde', 'bar', 'vec', 'dot', 'ddot'
]


PRIMES = {'prime': "'", '2prime': "''", '3prime': "'''"}

# what will be appended after the names to store units for those names
UNIT_PF = '___0UNIT0'

class _LatexVisitor(ast.NodeVisitor):

    def __init__(self, mul_symbol, div_symbol, subs, mat_size):
        self.mul_symbol = mul_symbol
        self.div_symbol = div_symbol
        self.subs = subs
        self.mat_size = mat_size

    def prec(self, n):
        return getattr(self, 'prec_'+n.__class__.__name__, getattr(self, 'generic_prec'))(n)

    # attributes (foo.bar)
    def visit_Attribute(self, n):
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
        args = ', '.join([self.visit(arg) for arg in n.args])
        if func == 'sqrt':
            return fr'\sqrt{{{args}}}'
        return fr'\operatorname{{{func}}}\left({args}\right)'

    def prec_Call(self, n):
        return 1000

    def format_name(self, name_str):
        parts = name_str.strip(' _').split('_')
        parts_final = parts[:]
        accent_locations = []
        for index, part in enumerate(parts):
            # no modification is wanted if the first character is 0
            if part.startswith('0') and len(part) > 1:
                parts_final[index] = fr'\mathrm{{{part[1:]}}}'
            # convert to latex commands
            elif part in GREEK_LETTERS:
                parts_final[index] = '{\\' + part + '}'
            # enclose the previous item in accent commands
            elif part in MATH_ACCENTS:
                # (to choose which to surround)
                which = index - 2 if not parts[index - 1] else index - 1
                parts_final[which] = '{\\' + f'{part}{{{parts_final[which]}}}}}'
                accent_locations.append(index)
            # convert primes
            elif part in PRIMES.keys():
                which = index - 2 if not parts[index - 1] else index - 1
                parts_final[which] = '{' + parts_final[which] + PRIMES[part] + "}"
                accent_locations.append(index)
            elif len(part) > 1:
                parts_final[index] = fr'\mathrm{{{parts_final[index]}}}'
        # remove the accents
        parts_final = [part for index, part in enumerate(parts_final)
                        if index not in accent_locations]
        name = '_'.join(parts_final).replace('__', '^')

        return name

    # variables
    def visit_Name(self, n):
        if self.subs:
            # substitute the value of the variable by formatted value
            from .formatting import format_quantity
            from __main__ import __dict__
            try:
                qty = format_quantity(__dict__[n.id], self.mat_size)
                unit = __dict__[n.id + UNIT_PF] \
                    if n.id + UNIT_PF in __dict__.keys() else ''
            except KeyError:
                raise UserWarning(f"The variable '{n.id}' has not been defined.")
            return qty + unit
        return self.format_name(n.id)

    def prec_Name(self, n):
        return 1000

    def visit_UnaryOp(self, n):
        if self.prec(n.op) > self.prec(n.operand):
            return fr'{ self.visit(n.op) } \left({ self.visit(n.operand) }\right)'
        else:
            return fr'{ self.visit(n.op) } { self.visit(n.operand) }'

    def prec_UnaryOp(self, n):
        return self.prec(n.op)

    def visit_BinOp(self, n):
        if self.prec(n.op) > self.prec(n.left):
            left = fr'\left({ self.visit(n.left) }\right)'
        else:
            left = self.visit(n.left)
        if self.prec(n.op) > self.prec(n.right):
            right = fr'\left({ self.visit(n.right) }\right)'
        else:
            right = self.visit(n.right)
        if isinstance(n.op, ast.Mult) and isinstance(n.right, ast.Name):
            if not self.subs:
                return fr'{self.visit(n.left)} \, {self.visit(n.right)}'
        elif isinstance(n.op, ast.Pow):
            return fr'{self.visit(n.left)}^{{{self.visit(n.right)}}}'
        elif self.div_symbol == 'frac':
            if isinstance(n.op, ast.Div):
                return fr'\frac{{{ self.visit(n.left) }}}{{{ self.visit(n.right) }}}'
            elif isinstance(n.op, ast.FloorDiv):
                return fr'\left\lfloor\frac{{{ self.visit(n.left) }}}{{{ self.visit(n.right) }}}\right\rfloor'
        return fr'{left} {self.visit(n.op)} {right}'

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
            return '\\times'
        elif self.mul_symbol == '.':
            return '\\cdot'
        return r'\,'

    def prec_Mult(self, n):
        return 400

    def visit_Mod(self, n):
        return '\\bmod'

    def prec_Mod(self, n):
        return 500

    def prec_Pow(self, n):
        return 700

    def visit_Div(self, n):
        if self.div_symbol == '/':
            return '\\slash'
        else:
            return '\\div'

    def prec_Div(self, n):
        return 400

    def prec_FloorDiv(self, n):
        return 400

    def visit_LShift(self, n):
        return '\\operatorname{shiftLeft}'

    def visit_RShift(self, n):
        return '\\operatorname{shiftRight}'

    def visit_BitOr(self, n):
        return '\\operatorname{or}'

    def visit_BitXor(self, n):
        return '\\operatorname{xor}'

    def visit_BitAnd(self, n):
        return '\\operatorname{and}'

    def visit_Invert(self, n):
        return '\\operatorname{invert}'

    def prec_Invert(self, n):
        return 800

    def visit_Not(self, n):
        return '\\neg'

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

    def visit_Num(self, n):
        return str(n.n)

    def prec_Num(self, n):
        return 1000

    def generic_visit(self, n):
        if isinstance(n, ast.AST):
            return r'' % (n.__class__.__name__, ', '.join(map(self.visit, [getattr(n, f) for f in n._fields])))
        else:
            return str(n)

    def generic_prec(self, n):
        return 0


def latexify(expr, mul_symbol='*', div_symbol='frac', subs=False, mat_size=5):
    if expr:
        pt = ast.parse(expr.strip())
        return _LatexVisitor(mul_symbol, div_symbol, subs, mat_size).visit(pt.body[0].value)
    return ''

def _surround_equation(equation: str, disp: bool):
    '''surround given equation by latex surroundings/ environments'''

    equation_len = 1 + equation.count('\n')

    if equation_len == 1:
        if disp:
            output_equation = ('\\begin{equation}\n'
                               f'{equation}\n'
                               '\\end{equation}')
        else:
            output_equation = fr'\({equation}\)'
    else:
        output_equation = ('\\begin{align}\n\\begin{split}\n'
                           f'{equation}\n'
                           '\\end{split}\n\\end{align}')

    return output_equation

def _equation_raw(*equations):
    '''Modify [many] latex equations so they can be aligned vertically '''

    if len(equations) == 1:
        output_equation = equations[0]

    else:
        output_equation = '\\\\\n'.join(
            [equation.replace('=', '&=') for equation in equations])

    return output_equation


def _equation_normal(*equations):
    ''' convert [many] string equations from python form to latex '''

    if len(equations) > 1:
        equals = ' &= '
    else:
        equals = ' = '

    equations_formatted = [equals.join([latexify(expr.strip())
                                        for expr in equation.split('=')])
                           for equation in equations]

    output_equation = '\\\\\n'.join(equations_formatted)

    return output_equation


def eqn(*equation_list, norm: bool = True, disp: bool = True):
    '''main api for equations'''

    if norm:
        output_equation = _equation_normal(*equation_list)
    else:
        output_equation = _equation_raw(*equation_list)

    return _surround_equation(output_equation, disp)

