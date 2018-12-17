'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calsulations
'''

import ast  # to know deduce which steps are needed
from .document import DICT
from .parsing import latexify, eqn, format_quantity, DEFAULT_MAT_SIZE, UNIT_PF


def _calculate(expr, steps, mat_size):
    '''carryout the necesary calculations and assignments'''

    result = []
    for step in steps:
        if step == 0:
            result.append(latexify(expr, mul_symbol='.', mat_size=mat_size))
        elif step == 1:
            result.append(latexify(expr, mul_symbol='*',
                                   subs=True, mat_size=mat_size))
        elif step == 2:
            result.append(format_quantity(eval(expr, DICT), mat_size))

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

    if unit:
        if unit == 'deg':
            unit = '^\\circ'
        else:
            unit = f" \, \mathrm{{{latexify(unit, mul_symbol=' ', div_symbol='/')}}}"

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
    result[-1] += unit + note

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
    if unit:
        for var in unp_vars:
            exec(f'{var}{UNIT_PF} = "{unit}"', DICT)

    return output
