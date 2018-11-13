# -ipy
'''
python expression to latex converter with import prefixes removal and optional
substitution of values from the main script, based on Geoff Reedy's answer to
https://stackoverflow.com/questions/3867028/converting-a-python-numeric-expression-to-latex
'''

import ast
from .formatting import format_quantity
from __main__ import __dict__ as globals_dict

GREEK_LETTERS = [
    'alpha', 'nu', 'beta', 'xi', 'Xi', 'gamma', 'Gamma', 'delta', 'Delta',
    'pi', 'Pi', 'epsilon', 'varepsilon', 'rho', 'varrho', 'zeta', 'sigma',
    'Sigma', 'eta', 'tau', 'theta', 'vartheta', 'Theta', 'upsilon', 'Upsilon',
    'iota', 'phi', 'varphi', 'Phi', 'kappa', 'chi', 'lambda', 'Lambda', 'psi',
    'Psi', 'mu', 'omega', 'Omega'
]

class _LatexVisitor(ast.NodeVisitor):

    def __init__(self, mul_symbol, div_symbol, subs):
        self.mul_symbol = mul_symbol
        self.div_symbol = div_symbol
        self.subs = subs

    def prec(self, n):
        return getattr(self, 'prec_'+n.__class__.__name__, getattr(self, 'generic_prec'))(n)

    # function calls
    def visit_Call(self, n):
        # remove the import prefixes
        if isinstance(n.func, ast.Attribute):
            func = self.visit(n.func.attr)
        else:
            func = self.visit(n.func)
        args = ', '.join([self.visit(arg) for arg in n.args])
        if func == 'sqrt':
            return f'\sqrt{{{args}}}'
        else:
            return fr'\operatorname{{{func}}}\left({args}\right)'

    def prec_Call(self, n):
        return 1000

    # variables
    def visit_Name(self, n):
        if self.subs:
            # substitute the value of the variable by formatted value
            return format_quantity(globals_dict[n.id])
            # pass
        else:
            # convert __ to ^ and enclose words in the name
            parts = n.id.split('_')
            if parts[0] in GREEK_LETTERS:
                parts[0] = '\\' + parts[0]
            for n in range(1, len(parts)):
                if parts[n] in GREEK_LETTERS:
                    parts[n] = '{\\' + parts[n] + '}'
                elif parts[n] != '':
                    parts[n] = '{' + parts[n] + '}'
            name = '_'.join(parts).replace('__', '^')
            return name

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
        if self.div_symbol == 'frac':
            if isinstance(n.op, ast.Div):
                return fr'\frac{{{ self.visit(n.left) }}}{{{ self.visit(n.right) }}}'
            elif isinstance(n.op, ast.FloorDiv):
                return fr'\left\lfloor\frac{{{ self.visit(n.left) }}}{{{ self.visit(n.right) }}}\right\rfloor'
        elif isinstance(n.op, ast.Pow):
            return fr'{left}^{{{ self.visit(n.right) }}}'
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
        return '\\;'

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

def latexify(expr, mul_symbol=' ', div_symbol='-:-', subs=False):
    pt = ast.parse(expr)
    return _LatexVisitor(mul_symbol, div_symbol, subs).visit(pt.body[0].value)
