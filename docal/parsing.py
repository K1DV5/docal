# -ipy
'''
python expression to latex converter with import prefixes removal and optional
substitution of values from the main script, based on Geoff Reedy's answer to
https://stackoverflow.com/questions/3867028/converting-a-python-numeric-expression-to-latex
'''

import ast
import re
from .document import DICT, color

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

# what will be appended after the names to store units for those names
UNIT_PF = '___0UNIT0'


def _prep4lx(quantity, mat_size=(DEFAULT_MAT_SIZE, DEFAULT_MAT_SIZE)):
    '''
    parse the given quantity to an AST object so it can be integrated in _LatexVisitor
    '''

    quantity_type = str(type(quantity))
    ndquantities = ['array', 'Array', 'matrix', 'Matrix']

    if any([typ in quantity_type for typ in ndquantities]):
        if isinstance(mat_size, int):
            mat_size = (mat_size, mat_size)

        quantity = _fit_matrix(quantity, mat_size)

    return ast.parse(str(quantity)).body[0].value


def _fit_array(array, max_size=5):
    '''
    shorten the given 1 dimensional matrix/array by substituting ellipsis (...)
    '''

    if len(array) > max_size:
        array = [*array[:max_size - 2], '\\vdots', array[-1]]

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


def _fit_matrix(matrix, max_size=(5, 5)):
    '''
    if there is a need, make the given matrix smaller
    '''

    shape = matrix.shape
    # array -> short
    if len(shape) == 1 and shape[0] > max_size[0]:
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

    def __init__(self, mul_symbol, div_symbol, subs, mat_size):
        self.mul_symbol = mul_symbol
        self.div_symbol = div_symbol
        self.subs = subs
        self.mat_size = mat_size

    def prec(self, n):
        return getattr(self, 'prec_'+n.__class__.__name__, getattr(self, 'generic_prec'))(n)

    # attributes (foo.bar)
    def visit_Attribute(self, n, raw=False):
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
            if raw:
                return _prep4lx(eval(f'{base}.{attr}', DICT), self.mat_size)
            # get, prep and visit the value
            return self.visit(_prep4lx(eval(f'{base}.{attr}', DICT), self.mat_size))
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
        ignored = ['round', 'matrix', 'Matrix', 'array', 'ndarray']
        if func == 'sqrt':
            return fr'\sqrt{{{args}}}'
        elif func == 'inv':
            return f'{{{args}}}^{{-1}}'
        elif func == 'transpose':
            return f'{{{args}}}^{{T}}'
        elif func in ignored:
            return self.visit(n.args[0])
        return fr'\operatorname{{{func}}}\left({args}\right)'

    def prec_Call(self, n):
        return 1000

    def visit_Lambda(self, n):
        return self.visit(n.body)

    def prec_Lambda(self, n):
        return self.prec(n.body)

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

    # variables
    def visit_Name(self, n, raw=False):
        if self.subs:
            # substitute the value of the variable by formatted value
            try:
                # if the raw ast object is needed (for BinOp)
                if raw:
                    return _prep4lx(DICT[n.id], self.mat_size)
                # to prevent infinite recursion:
                if str(DICT[n.id]) == n.id:
                    return self.format_name(str(DICT[n.id]))
                qty = self.visit(_prep4lx(DICT[n.id], self.mat_size))
                unit = fr'\, \mathrm{{{latexify(DICT[n.id + UNIT_PF], div_symbol="/")}}}' \
                    if n.id + UNIT_PF in DICT.keys() and DICT[n.id + UNIT_PF] and DICT[n.id + UNIT_PF] != '_' else ''
                # if the quantity is raised to some power and has a unit,
                # surround it with parens
                if hasattr(n, 'is_in_power') and n.is_in_power and unit and unit != '_':
                    return f'\\left({qty} {unit}\\right)'
                return qty + unit
            except KeyError:
                print(color('WARNING', 'yellow'),
                      f" The variable '{color(n.id, 'red')}' has not been defined.")
        return self.format_name(n.id)

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
            # so that it can be surrounded with parens if it has units
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
        return '\\left[\\begin{matrix}\n' + '\\\\\n'.join(elements) + '\n\\end{matrix}\\right]'

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
        return '\\left(' + ', '.join([self.visit(element) for element in n.elts]) + '\\right)'

    def prec_Tuple(self, n):
        return 1000

    # indexed items (item[4:])
    def visit_Subscript(self, n):
        # if the iterable is kinda not simple, surround it with parens
        if isinstance(n.value, ast.BinOp) or isinstance(n.value, ast.UnaryOp):
            return f'{{\\left({self.visit(n.value)}\\right)}}_{{\\left[{self.visit(n.slice)}\\right]}}'
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
        if re.match('\w*', n.s).span()[1] == len(n.s):
            return self.format_name(n.s)
        # or if it seems like an equation
        elif re.search(r'[^=]=[^w]', n.s):
            return eqn(n.s)
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


def latexify(expr, mul_symbol='*', div_symbol='frac', subs=False, mat_size=5):
    '''
    convert the given expr to a latex string using _LatexVisitor
    '''

    if isinstance(expr, str):
        if expr:
            pt = ast.parse(expr.strip()).body[0].value
        else:
            return ''
    else:
        pt = _prep4lx(expr)

    return _LatexVisitor(mul_symbol, div_symbol, subs, mat_size).visit(pt)


def eqn(*equation_list, norm: bool = True, disp: bool = True, surr: bool = True):
    '''main api for equations'''

    eqn_len = len(equation_list)
    equals = ' = '
    joint = ' \\; '

    if disp:
        if eqn_len > 1:
            surroundings = [
                '\\begin{align}\n\\begin{split}\n', '\n\\end{split}\n\\end{align}']
            equals = ' &= '
            joint = '\\\\\n'
        else:
            surroundings = ['\\begin{equation}\n', '\n\\end{equation}']
    else:
        surroundings = ['\\(\\displaystyle ', ' \\)']

    if norm:
        equations = [equals.join([latexify(expr.strip())
                                  for expr in equation.split('=')])
                     for equation in equation_list]
    else:
        equations = [equation.replace('=', equals)
                     for equation in equation_list]

    if surr:
        return surroundings[0] + joint.join(equations) + surroundings[1]
    return joint.join(equations)
