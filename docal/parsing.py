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
from .utils import _split

DEFAULT_MAT_SIZE = 10

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

# things that are transformed, used for units and such
TRANSFORMED = {
    'degC': '\\,^\\circ \\mathrm{C}',
    'degF': '\\,^\\circ \\mathrm{F}',
    'deg': '\\,^\\circ'
}

# what will be appended after the names to store units for those names
UNIT_PF = '___0UNIT0'


def format_name(name_str: str) -> str:
    '''
    Turn a variable name into a latex term that has sub/superscripts, accents,
    upright if needed, and prime signs
    '''
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
        # maybe if it is something that is simpler to write than its value
        elif part in TRANSFORMED:
            parts_final[index] = TRANSFORMED[part]
        # enclose the previous item in accent commands
        elif part in MATH_ACCENTS:
            # (to choose which to surround)
            which = index - 2 if not parts[index - 1] else index - 1
            parts_final[which] = '{\\' + \
                f'{part}{{{parts_final[which]}}}}}'
            accent_locations.append(index)
        # convert primes
        elif part in PRIMES.keys():
            which = index - 2 if not parts[index - 1] else index - 1
            parts_final[which] = '{' + \
                parts_final[which] + PRIMES[part] + "}"
            accent_locations.append(index)
        elif len(part) > 1:
            parts_final[index] = fr'\mathrm{{{parts_final[index]}}}'
    # remove the accents
    parts_final = [part for index, part in enumerate(parts_final)
                   if index not in accent_locations]
    name = '_'.join(parts_final).replace('__', '^')

    return name


def _prep4lx(quantity, mat_size=(DEFAULT_MAT_SIZE, DEFAULT_MAT_SIZE)):
    '''
    parse the given quantity to an AST object so it can be integrated in _LatexVisitor
    '''

    quantity_type = str(type(quantity))
    ndquantities = ['array', 'Array', 'matrix', 'Matrix', 'list']

    if any([typ in quantity_type for typ in ndquantities]):
        if isinstance(mat_size, int):
            mat_size = (mat_size, mat_size)

        quantity = _fit_matrix(quantity, mat_size)

    return ast.parse(str(quantity)).body[0]


def _fit_array(array, mat_size=DEFAULT_MAT_SIZE):
    '''
    shorten the given 1 dimensional matrix/array by substituting ellipsis (...)
    '''

    if len(array) > mat_size:
        array = [*array[:mat_size - 2], '\\vdots', array[-1]]

    return array


def _fit_big_matrix(matrix, size):
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
        element += ['\\cdots', last_col[index][0]]
    mat.append(['\\vdots'] * (cols - 2) + ['\\ddots', '\\vdots'])
    mat.append(last_row[0] + ['\\cdots', last_element])

    return mat


def _fit_wide_matrix(matrix, max_cols):
    '''
    make the wide matrix narrower by substituting horizontal ... in the rows
    '''

    mat = matrix[:, :max_cols - 2].tolist()
    last_col = matrix[:, -1].tolist()
    for index, element in enumerate(mat):
        element += ['\\cdots', last_col[index][0]]

    return mat


def _fit_long_matrix(matrix, max_rows):
    '''
    shorten the matrix by substituting vertical ... in the columns
    '''

    mat = matrix[:max_rows - 2, :].tolist()
    mat += [['\\vdots'] * matrix.shape[1]]
    mat += matrix[-1, :].tolist()

    return mat


def _fit_matrix(matrix, max_size=(DEFAULT_MAT_SIZE, DEFAULT_MAT_SIZE)):
    '''
    if there is a need, make the given matrix smaller
    '''

    shape = (len(matrix),) if isinstance(matrix, list) else matrix.shape
    # array -> short
    if len(shape) == 1 and shape[0] > max_size[0] or isinstance(matrix, list):
        mat_ls = _fit_array(matrix, max_size[0])
    # too big -> small
    elif matrix.shape[0] > max_size[0] and matrix.shape[1] > max_size[1]:
        mat_ls = _fit_big_matrix(matrix, max_size)
    # too long -> small
    elif matrix.shape[0] > max_size[0] and matrix.shape[1] < max_size[1]:
        mat_ls = _fit_long_matrix(matrix, max_size[0])
    # too wide -> small
    elif matrix.shape[0] < max_size[0] and matrix.shape[1] > max_size[1]:
        mat_ls = _fit_wide_matrix(matrix, max_size[1])
    # already small so :)
    else:
        mat_ls = matrix.tolist()

    return mat_ls


class _LatexVisitor(ast.NodeVisitor):

    def __init__(self, mul_symbol, div_symbol, subs, mat_size, working_dict=DICT):
        self.mul_symbol = mul_symbol
        self.div_symbol = div_symbol
        self.subs = subs
        self.mat_size = mat_size
        self.dict = working_dict

    def prec(self, n):
        return getattr(self, 'prec_'+n.__class__.__name__, getattr(self, 'generic_prec'))(n)

    def visit_Expr(self, n):
        return self.visit(n.value)

    def visit_Assign(self, n):
        return ' = '.join([self.visit(t) for t in n.targets + [n.value]])

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
        return format_name(n.attr)

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
        ignored = ['round', 'matrix', 'Matrix', 'array', 'ndarray']
        if func == 'sqrt':
            return fr'\sqrt{{{args}}}'
        elif func == 'inv':
            return f'{{{args}}}^{{-1}}'
        elif func == 'transpose':
            return f'{{{args}}}^{{T}}'
        elif func == 'sum':
            if isinstance(n.args[0], ast.Name):
                n.args[0] = self.visit_Name(n.args[0], True)
            if isinstance(n.args[0], ast.List) or isinstance(n.args[0], ast.Tuple):
                return fr'\sum_{{i = 1}}^{{{len(n.args[0].elts)}}} {args}'
            else:
                return fr'\sum \left({args}\right)'
        elif func == 'log':
            return fr'\ln {args}'
        elif func == 'log10':
            return fr'\log {args}'
        elif func == 'log2':
            return fr'\log_2 {args}'
        elif func in ignored:
            return self.visit(n.args[0])
        return fr'\operatorname{{{func}}}\left({args}\right)'

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
                    return _prep4lx(self.dict[n.id], self.mat_size).value
                # to prevent infinite recursion:
                if str(self.dict[n.id]) == n.id:
                    return format_name(str(self.dict[n.id]))
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
                logging.warning('The variable %s has not been defined.', n.id)
        return format_name(n.id)

    def prec_Name(self, n):
        return 1000

    def visit_UnaryOp(self, n):
        if isinstance(n.op, ast.USub):
            n.operand.is_in_unaryop = True
        if self.prec(n.op) >= self.prec(n.operand) \
                or (hasattr(n, 'is_in_unaryop') and n.is_in_unaryop):
            return fr'{ self.visit(n.op) } \left({ self.visit(n.operand) }\right)'
        else:
            return fr'{ self.visit(n.op) } { self.visit(n.operand) }'

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
        if self.prec(n.op) > self.prec(n.left):
            left = fr'\left({ self.visit(n.left) }\right)'
        else:
            left = self.visit(n.left)
        if self.prec(n.op) > self.prec(tmp_right):
            # not forgetting the units, so n.right
            right = fr'\left({ self.visit(n.right) }\right)'
        else:
            right = self.visit(n.right)
        if isinstance(n.op, ast.Mult):
            # unless the right term is a Num or BinOp whose operation is power
            no_need = not any([isinstance(tmp_right, ast.BinOp)
                               and isinstance(tmp_right.op, ast.Pow)
                               and isinstance(tmp_right.left, ast.Num),
                               isinstance(tmp_right, ast.Num)])
            if no_need:
                return fr'{left} \, {right}'
        elif isinstance(n.op, ast.Pow):
            # so that it can be surrounded with PARENS if it has units
            n.left.is_in_power = True
            return fr'{self.visit(n.left)}^{{{right}}}'
        elif self.div_symbol == 'frac':
            if isinstance(n.op, ast.Div):
                return fr'\frac{{{left}}}{{{right}}}'
            elif isinstance(n.op, ast.FloorDiv):
                return fr'\left\lfloor\frac{{{left}}}{{{right}}}\right\rfloor'
        return fr'{left} {self.visit(n.op)} {right}'

    def prec_BinOp(self, n):
        return self.prec(n.op)

    def visit_List(self, n):
        if hasattr(n, 'is_in_list') and n.is_in_list:
            elements = [self.visit(element) for element in n.elts]
            return ' & '.join(elements)
        for child in ast.iter_child_nodes(n):
            if isinstance(child, ast.List):
                child.is_in_list = True
        elements = [self.visit(element) for element in n.elts]
        return ('\\left[\\begin{matrix}\n'
                + '\\\\\n'.join(elements)
                + '\n\\end{matrix}\\right]')

    def prec_List(self, n):
        return 1000

    def visit_Tuple(self, n):
        # if it is used as an index for an iterable, add 1 to the elements if
        # they are numbers
        if hasattr(n, 'is_in_index') and n.is_in_index:
            return ', '.join([str(int(i.n) + 1)
                              if isinstance(i, ast.Num)
                              else self.visit(i)
                              for i in n.elts])
        return ('\\left('
                + ', '.join([self.visit(element) for element in n.elts])
                + '\\right)')

    def prec_Tuple(self, n):
        return 1000

    # indexed items (item[4:])
    def visit_Subscript(self, n):
        # if the iterable is kinda not simple, surround it with PARENS
        if isinstance(n.value, ast.BinOp) or isinstance(n.value, ast.UnaryOp):
            return (f'{{\\left({self.visit(n.value)}\\right)}}'
                    f'_{{\\left[{self.visit(n.slice)}\\right]}}')
        # write the indices as subscripts
        return f'{{{self.visit(n.value)}}}_{{\\left[{self.visit(n.slice)}\\right]}}'

    def visit_Index(self, n):
        # this will be used by the tuple visitor
        n.value.is_in_index = True
        # if it is a number, add 1 to it
        if isinstance(n.value, ast.Num):
            return str(int(n.value.n) + 1)
        return self.visit(n.value)

    def visit_Slice(self, n):
        # same thing with adding one
        lower, upper = [str(int(i.n) + 1)
                        if isinstance(i, ast.Num)
                        else self.visit(i)
                        for i in [n.lower, n.upper]]
        # join the upper and lower limits with -
        return self.visit(lower) + '-' + self.visit(upper)

    def visit_ExtSlice(self, n):
        return ', '.join([self.visit(s) for s in n.dims])

    def visit_Str(self, n):
        # if whole string contains only word characters
        if re.match(r'\w*', n.s).span()[1] == len(n.s):
            return format_name(n.s)
        # or if it seems like an equation
        elif re.search(r'[^=]=[^w]', n.s):
            try:
                # can't use latexify because the equations may be
                # python illegal and latex legal like 3*4 = 5/6
                return eqn(n.s, surr=False, vert=False)
            except SyntaxError:  # if the equation is just beyond understanding
                pass
        return n.s

    def prec_Str(self, n):
        return 1000

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
        number = n.n
        if number != 0 and (abs(number) > 1000 or abs(number) < 0.1):
            # in scientific notation
            num_ls = f'{number:.2E}'.split('E')
            # remove the preceding zeros and + in the powers like +07 to just 7
            num_ls[1] = num_ls[1][0].lstrip('+') + num_ls[1][1:].lstrip('0')
            # make them appear as powers of 10
            return num_ls[0] + '\\left(10^{' + num_ls[1] + '}\\right)'
        if number == int(number):
            return str(int(number))
        return str(round(number, 2))

    def prec_Num(self, n):
        if hasattr(n, 'is_in_power') and n.is_in_power \
                and n.n != 0 and (abs(n.n) > 1000 or abs(n.n) < 0.1):
            return 300
        return 1000

    def generic_visit(self, n):
        return str(n)

    def generic_prec(self, n):
        return 0


def latexify(expr, mul_symbol='*', div_symbol='frac', subs=False, mat_size=DEFAULT_MAT_SIZE, working_dict=DICT):
    '''
    convert the given expr to a latex string using _LatexVisitor
    '''

    if isinstance(expr, str):
        if expr.strip():
            pt = ast.parse(expr.strip()).body[0]
        else:
            return ''
    else:
        pt = _prep4lx(expr, mat_size)

    return _LatexVisitor(mul_symbol, div_symbol, subs, mat_size, working_dict).visit(pt)


def eqn(*equation_list, norm: bool = True, disp: bool = True, surr: bool = True,
        vert: bool = True) -> str:
    '''main api for equations'''

    equals = ' = '
    joint = ' \\; '

    if disp:
        if len(equation_list) > 1:
            surroundings = [
                '\\begin{align}\n\\begin{split}\n', '\n\\end{split}\n\\end{align}']
            if vert:
                joint = '\\\\\n'
                equals = ' &= '
        else:
            surroundings = ['\\begin{equation}\n', '\n\\end{equation}']
    else:
        surroundings = ['\\(\\displaystyle ', ' \\)']

    if norm:
        equations = []
        for eq in equation_list:
            left, right = _split(eq)
            left = ' = '.join([latexify(e) for e in _split(left, last=False)])
            equations.append(equals.join([left, latexify(right)]))
    else:
        equations = [equals.join(_split(eq)) for eq in equation_list]

    if surr:
        return surroundings[0] + joint.join(equations) + surroundings[1]
    return joint.join(equations)
