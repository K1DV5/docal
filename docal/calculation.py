'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calsulations
'''

import ast  # to know deduce which steps are needed
from .document import DICT
from .parsing import latexify, eqn, DEFAULT_MAT_SIZE, UNIT_PF


def _calculate(expr, steps, mat_size):
    '''carryout the necesary calculations and assignments'''

    result = []
    for step in steps:
        if step == 0:
            result.append(latexify(expr, mat_size=mat_size))
        elif step == 1:
            result.append(latexify(expr, subs=True, mat_size=mat_size))
        elif step == 2:
            result.append(latexify(eval(expr, DICT), mat_size))

    return result


def figure_out_steps(expr_dump):
    '''used when nothing about the steps comes from the user to prevent repetition
    when the calculation is sent to the pdf. return necessary steps based on the
    expression content.'''

    # there are no calls or ops in the expression
    if not (any([typ in expr_dump for typ in ['Call', 'BinOp', 'UnaryOp']])):
        if 'Name' in expr_dump:
            steps = [0, 2]
        else:
            steps = [2]
    else:
        if 'Name' in expr_dump:
            steps = [0, 1, 2]
        else:
            steps = [0, 2]

    return steps


def _assort_input(input_str):
    '''look above'''

    # only split once, because the # char is used for notes below
    input_parts = [part.strip() for part in input_str.strip().split('#', 1)]
    if len(input_parts) == 1:
        additionals = ''
        equation = input_str
    else:
        equation = input_parts[0]
        additionals = input_parts[1]

    var_name, expression = [part.strip() for part in equation.split('=', 1)]
    unp_vars = [n.id
                for n in ast.walk(ast.parse(var_name).body[0].value)
                if isinstance(n, ast.Name)]
    expr_dump = ast.dump(ast.parse(expression))

    steps = figure_out_steps(expr_dump)
    mat_size = DEFAULT_MAT_SIZE
    unit = ''
    mode = 'default'
    note = ''

    for a in [a.strip() for a in additionals.split(',')]:
        if a.isdigit():
            steps = [int(num) - 1 for num in a]
        # only the first # is used to split the line (see above) so others
        elif a.startswith('#'):
            note = a[1:]
        elif a.startswith('m') and a[1:].isdigit():
            if len(a) == 2:
                mat_size = int(a[1])
            else:
                mat_size = (int(a[1]), int(a[2]))
        elif a == '$':
            mode = 'inline'
        elif a == '$$':
            mode = 'display'
        else:
            unit = a

    if note:
        note = f'\\quad\\text{{{note}}}'

    return var_name, unp_vars, expression, unit, steps, mat_size, mode, note


def cal(input_str):
    '''
    evaluate all the calculations, carry out the appropriate assignments,
    and return all the procedures

    '''
    var_name, unp_vars, expr, unit, steps, mat_size, mode, note = _assort_input(
        input_str)
    result = _calculate(expr, steps, mat_size)
    var_lx = latexify(var_name)
    if not unit:
        unit = unitize(expr)
    if unit == 'deg':
        unit_lx = '^\\circ'
    elif unit == 'degC':
        unit_lx = '^\\circ C'
    elif unit == 'degF':
        unit_lx = '^\\circ F'
    else:
        unit_lx = f" \, \mathrm{{{latexify(unit, div_symbol='/')}}}"
    result[-1] += unit_lx + note

    if mode == 'inline':
        displ = False
    elif mode == 'display':
        displ = True
    else:
        if len(steps) == 1 and steps[0] == 0:
            displ = False
        else:
            displ = True

    procedure = [f'{var_lx} = {result[0]}']
    for step in result[1:]:
        procedure.append('    = ' + step)

    output = eqn(*procedure, norm=False, disp=displ)

    # carry out normal op in main script
    exec(input_str, DICT)
    # for later unit retrieval
    for var in unp_vars:
        exec(f'{var}{UNIT_PF} = "{unit}"', DICT)

    return output

class UnitHandler(ast.NodeVisitor):
    '''
    simplify the given expression as a combination of units
    '''
    def __init__(self, norm=False):
        self.norm = norm

    def visit_Name(self, n):
        if self.norm:
            unit = n
        else:
            un = DICT[n.id + UNIT_PF]
            unit = ast.parse(un if un else '_').body[0].value
        if isinstance(unit, ast.Name):
            if hasattr(n, 'upper') and not n.upper:
                return [{}, {unit.id: 1}]
            else:
                return [{unit.id: 1}, {}]
        else:
            unit.upper = n.upper
            self.norm = True
            l = self.visit(unit)
            self.norm = False
            return l

    def visit_Call(self, n):
        if isinstance(n.func, ast.Attribute):
            func = n.func.attr
        elif isinstance(n.func, ast.Name):
            func = n.func.id
        else:
            func = self.visit(n.func)
        if func == 'sqrt':
            return self.visit(ast.BinOp(left=n.args[0], op=ast.Pow(), right=ast.Num(n=1/2)))
        return [{}, {}]
        
    def visit_BinOp(self, n):
        if hasattr(n, 'upper') and not n.upper:
            upper = False
        else:
            upper = True
        n.left.upper = upper
        left = self.visit(n.left)
        if isinstance(n.op, ast.Pow):
            if isinstance(n.right, ast.BinOp):
                if isinstance(n.right.left, ast.Num) and isinstance(n.right, ast.Num):
                    if isinstance(n.right.op, ast.Add):
                        p = n.right.left.n + n.right.n
                    elif isinstance(n.right.op, ast.Sub):
                        p = n.right.left.n - n.right.n
                    elif isinstance(n.right.op, ast.Mult):
                        p = n.right.left.n * n.right.n
                    elif isinstance(n.right.op, ast.Div):
                        p = n.right.left.n / n.right.n
                    elif isinstance(n.right.op, ast.Pow):
                        p = n.right.left.n ** n.right.n
            elif isinstance(n.right, ast.UnaryOp):
                if isinstance(n.operand, ast.Num):
                    if isinstance(n.op, ast.USub):
                        p = - n.operand.n
                    elif isinstance(n.op, ast.UAdd):
                        p = n.operand.n
            elif isinstance(n.right, ast.Num):
                p = n.right.n
            for u in left[0]:
                left[0][u] *= p
            for u in left[1]:
                left[1][u] *= p
            return left
        elif isinstance(n.op, ast.Mult):
            n.right.upper = upper
            right = self.visit(n.right)
            for u in right[0]:
                if u in left[0]:
                    left[0][u] += right[0][u]
                else:
                    left[0][u] = right[0][u]
            for u in right[1]:
                if u in left[1]:
                    left[1][u] += right[1][u]
                else:
                    left[1][u] = right[1][u]
            return left
        elif isinstance(n.op, ast.Div):
            n.right.upper = not upper
            right = self.visit(n.right)
            for u in right[0]:
                if u in left[0]:
                    left[0][u] += right[0][u]
                else:
                    left[0][u] = right[0][u]
            for u in right[1]:
                if u in left[1]:
                    left[1][u] += right[1][u]
                else:
                    left[1][u] = right[1][u]
            return left
        elif isinstance(n.op, ast.Add):
            n.right.upper = upper
            left = cancel(left)
            right = cancel(self.visit(n.right))
            if (len(left[0]) == len(right[0]) and all([(e in right[0] and left[0][e] == right[0][e]) for e in left[0]])) \
                    and (len(left[1]) == len(right[1]) and all([(e in right[1] and left[1][e] == right[1][e]) for e in left[1]])):
                return left
            print('error')
            return [{}, {}]
    def visit_UnaryOp(self, n):
        return self.visit(n.operand)
    def generic_visit(self, n):
        return [{}, {}]


def unitize(s, norm=False):
    ls = cancel(UnitHandler(norm).visit(ast.parse(s).body[0].value))
    upper = ls[0]
    lower = ls[1]
    s_upper = f'({"*".join([u if upper[u] == 1 else u + "**" + str(upper[u]) for u in upper])})' if upper else "_"
    s_lower = f'/({"*".join([u if lower[u] == 1 else u + "**" + str(lower[u]) for u in lower])})' if lower else ""
    return s_upper + s_lower

def cancel(ls):
    '''
    cancel out units that appear in both the numerator and denominator, those
    that have no name (_) and those with power of 0
    '''
    upper = {**ls[0]}
    lower = {**ls[1]}
    for u in ls[0]:
        if u in ls[1]:
            if upper[u] > lower[u]:
                upper[u] -= lower[u]
                del lower[u]
            elif upper[u] < lower[u]:
                lower[u] -= upper[u]
                del upper[u]
            else:
                del upper[u]
                del lower[u]
    for u in {**upper}:
        if upper[u] == 0 or u == '_':
            del upper[u]
    for u in {**lower}:
        if lower[u] == 0 or u == '_':
            del lower[u]
    return [upper, lower]

