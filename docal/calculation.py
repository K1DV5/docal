'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calsulations
'''

import re
from sympy import latex, sympify, Symbol, Matrix
from sympy.physics.units import meter, second, kilogram, convert_to, Quantity
import __main__
from .equation import eqn

UNIT_ABBREVIATIONS = {'meter': 'm', 'millimeter': 'mm', 'second': 's',
                      'centimeter': 'cm', 'inch': 'in', 'kilogram': 'kg',
                      'pascal': 'Pa', 'newton': 'N'}


def _format_number(quantity, desired_unit):
    '''make the number part of a quantity more readable'''

    reduced_quantity = convert_to(quantity, [meter, kilogram, second])
    # if units cancel out
    if not reduced_quantity.atoms(Quantity):
        number = float(reduced_quantity)
    else:
        # if it is a sum (4*meter + 5*centimeter) or conversion is desired
        if 'Add' in str(type(quantity))\
                or desired_unit != (meter, kilogram, second):
            quantity = convert_to(quantity, desired_unit)
        number = float(list(quantity.evalf()
                            .as_coefficients_dict().values())[0])

    if number > 1000 or number < 0.1:
        # in scientific notation
        number = re.sub(r'([0-9]+)E([-+])([0-9]+)',
                        r'\1(10^{\2'+r'\g<3>'.lstrip(r'0')+r'})',
                        f'{number:.2E}').replace('+', '')
    else:
        if number == int(number):
            number = str(int(number))
        else:
            number = str(round(number, 3))

    return number


def _format_unit(quantity, desired_unit):
    '''make the unit conform to unit notation standards (more or less)'''

    # if the quantity is unitless or units cancel out
    if not sympify(quantity).atoms(Quantity) \
            or not convert_to(quantity,
                              [meter, kilogram, second]).atoms(Quantity):
        return ''

    # if it is a sum (4*meter + 5*centimeter) or conversion is desired
    if 'Add' in str(type(quantity))\
            or desired_unit != (meter, kilogram, second):
        quantity = convert_to(quantity, desired_unit)

    unit = ('\\,\\mathrm{'
            + latex(list(quantity.evalf().as_coefficients_dict().keys())[0],
                    mul_symbol='dot').replace('\\cdot', '\\,')
            + '}').replace('\\frac', '').replace('}{', '}\\slash{')

    for full_form, short_form in UNIT_ABBREVIATIONS.items():
        unit = re.sub(
            fr'(?<!_{{|[a-zA-Z_]{{2}}){full_form}(?![a-zA-Z_]+)',
            short_form, unit)

    return unit


def _format_array(array, desired_unit):
    '''look above'''

    if len(array) > 4:
        array = list(array[0:2]) + [array[-1]] # shorten

    number = latex(Matrix(array[:-1]))
    for element in array[:-1]:
        number = number.replace(latex(element),
                                _format_number(element, desired_unit),
                                1)
    number = number.replace('\\end{matrix}',
                            '\\\\\\vdots\\\\'
                            f'{_format_number(array[-1], desired_unit)}'
                            '\\end{matrix}')

    unit = _format_unit(array[0], desired_unit)

    return f'{number}{unit}'


def _format_big_matrix(matrix, desired_unit):
    '''look above'''

    matrix = matrix[:, :2].row_join(matrix[:, -1])  # make narrow
    matrix = matrix[:2, :].col_join(matrix[-1, :])  # shorten
    number = latex(matrix[:2, :2])
    for qty in matrix:
        number = number.replace(latex(qty), _format_number(qty, desired_unit))
    number = number\
        .replace('\\\\',
                 f' & \\cdots & {_format_number(matrix[0, -1], desired_unit)}'
                 '\\\\')\
        .replace('\\end{matrix}',
                 (f' & \\cdots & {_format_number(matrix[1, -1], desired_unit)}'
                  '\\\\\\vdots & \\vdots & \\ddots & \\vdots\\\\'
                  f'{_format_number(matrix[-1, 0], desired_unit)} '
                  f'& {_format_number(matrix[-1, 1], desired_unit)}'
                  f' & \\cdots & {_format_number(matrix[-1, -1], desired_unit)}'
                  '\\end{matrix}'))
    return number


def _format_wide_matrix(matrix, desired_unit):
    '''look above'''

    matrix = matrix[:, :2].row_join(matrix[:, -1])  # make narrow
    number = latex(matrix[:2, :2])
    line_breaks = number.count('\\\\')
    for row in range(0, line_breaks):
        number = number.replace(
            '\\\\',
            (' & \\cdots & {_format_number(matrix[row, -1], desired_unit)}'
             '\\temp'), 1)
    number = number.replace('\\temp', '\\\\')\
        .replace('\\end{matrix}',
                 ' & \\cdots & '
                 f'{_format_number(matrix[line_breaks, -1], desired_unit)}'
                 '\\end{{matrix}}')

    return number

def _format_long_matrix(matrix, desired_unit):
    '''look above'''

    matrix = matrix[:2, :].col_join(matrix[-1, :])  # shorten
    number = latex(matrix[:2, :2])
    for qty in matrix:
        number = number.replace(latex(qty), _format_number(qty, desired_unit))
    end_part = '\\\\\\vdots'
    ands = number.count('&', 0, number.find('\\\\'))
    for col in range(1, ands + 1):
        end_part += ' & \\vdots'
    end_part += f'\\\\{_format_number(matrix[-1, 0], desired_unit)}'
    for col in range(1, ands + 1):
        end_part += f' & {_format_number(matrix[-1, col], desired_unit)}'
    number = number.replace('\\end{matrix}', end_part + '\\end{matrix}')

    return number


def _format_matrix(matrix, desired_unit):
    '''look above'''

    matrix = Matrix(matrix)

    if matrix.rows > 4 and matrix.cols > 4:
        number = _format_big_matrix(matrix, desired_unit)
    elif matrix.rows > 4 and matrix.cols < 5:
        number = _format_long_matrix(matrix, desired_unit)
    elif matrix.rows < 5 and matrix.cols > 4:
        number = _format_wide_matrix(matrix, desired_unit)
    else:
        number = latex(matrix)
        for qty in matrix:
            number = number.replace(latex(qty),
                                    _format_number(qty, desired_unit))

    unit = _format_unit(matrix[0], desired_unit)

    return f'{number}{unit}'


def format_quantity(qty, desired_unit=(meter, kilogram, second)):
    '''returns a nicely latex formatted string of the quantity
    including the units (if any)'''

    qty_type = str(type(qty))

    if 'array' in qty_type or 'Array' in qty_type:
        formatted = _format_array(qty, desired_unit)

    elif 'matrix' in qty_type or 'Matrix' in qty_type:
        formatted = _format_matrix(qty, desired_unit)

    else:
        number = _format_number(qty, desired_unit)
        unit = _format_unit(qty, desired_unit)
        formatted = f'{number}{unit}'

    return formatted


class _calculation:
    '''the calculation entity'''

    def __init__(self, equation):
        '''prepare common variables for subsequent operations'''

        self.main_variable = equation.split('=')[0].strip()
        self.variable_lx = latex(sympify(self.main_variable))
        self.expr_0_str = equation.split('=')[1].strip()
        self.str_exp = re.sub(r'(?<![a-zA-Z_])[a-zA-Z]+\.(?=[a-zA-Z_]+)',
                              '', self.expr_0_str)
        self.sympified = sympify(self.str_exp)

    def step_one(self):
        '''the first step of the procedure'''

        expr_1_lx = latex(self.sympified, mul_symbol='dot')
        for full_form, short_form in UNIT_ABBREVIATIONS.items():
            if full_form in expr_1_lx:
                expr_1_lx = re.sub(
                    fr'(?<!_{{|[a-zA-Z_]{{2}}){full_form}(?![a-zA-Z_]+)',
                    f'\\mathrm{{{short_form}}}',
                    expr_1_lx)

        return expr_1_lx

    def step_two(self):
        '''the second step'''

        free_symbols = list(self.sympified.atoms(Symbol))
        variables_list = [latex(var) for var in free_symbols]
        values_list = [eval(str(var), __main__.__dict__)
                       for var in free_symbols]
        values_dict = dict(zip(variables_list, values_list))
        expr_2_lx = latex(self.sympified, mul_symbol='times')
        for var, val in values_dict.items():
            val_lx = format_quantity(val)
            expr_2_lx = re.sub(
                fr'(?<!_{{|[a-zA-Z_]{{2}}){re.escape(var)}\^?(?![a-zA-Z_]+)',
                lambda m: (fr'\left({val_lx}\right)^'
                           if m.group().endswith('^')
                           and '\\mathrm' in val_lx
                           else val_lx),
                expr_2_lx)

        return expr_2_lx

    def step_three(self, shown_unit):
        '''third step'''

        expr_3_lx = format_quantity(eval(self.expr_0_str, __main__.__dict__),
                                    shown_unit)

        return expr_3_lx

    def assign_variable(self, result_unit):
        '''the name says it'''

        if result_unit is None:
            main_value = self.expr_0_str
        else:
            try:
                main_value = convert_to(eval(self.expr_0_str,
                                             __main__.__dict__),
                                        result_unit)
            except:  # if it cannot be converted
                main_value = self.expr_0_str

        exec(f'{self.main_variable} = {main_value}', __main__.__dict__)



def cal(equation, intent='full', unit=None):
    '''
    evaluates all the calculations and assignment needed in the eqn
    and prints all the procedures
    (which can be inserted in a pweave or pythontex document)

    >>> cal('t_f = 56', 'd')
    $t_{f} = 56$

    >>> cal('r_d = sqrt(t_f/56)+78')
    <BLANKLINE>
    \\begin{align}
    \\begin{split}
    r_{d}       &= \\frac{\\sqrt{14}}{28} \\cdot \\sqrt{t_{f}} + 78\\\\
                &= \\frac{\\sqrt{14}}{28} \\times \\sqrt{56} + 78\\\\
                &= 79\\\\
    \\end{split}
    \\end{align}
    '''

    calc = _calculation(equation)
    calc.assign_variable(unit)

    _alignment_tabs = len(calc.variable_lx)//4

    if intent in ('define', 'd'):
        eqn(calc.variable_lx + ' = ' + calc.step_one(),
            norm=False, disp=False)

    elif intent in ('2step', '2'):
        eqn(calc.variable_lx + '\t= ' + calc.step_one(),
            _alignment_tabs * '\t' + '\t= ' + calc.step_three(unit),
            norm=False, disp=True)

    elif intent in ('last', 'l'):
        eqn(calc.variable_lx + '\t= ' + calc.step_three(unit),
            norm=False, disp=True)

    else:
        eqn(calc.variable_lx + '\t= ' + calc.step_one(),
            _alignment_tabs * '\t' + '\t= ' + calc.step_two(),
            _alignment_tabs * '\t' + '\t= ' + calc.step_three(unit),
            norm=False, disp=True)
