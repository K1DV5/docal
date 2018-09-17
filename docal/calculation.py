# -ipy
'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calsulations
'''

import re
from sympy import latex, sympify, Symbol, Matrix
from sympy.physics.units import meter, second, kilogram, convert_to, Quantity
import __main__
from .equation import eqn, _surround_equation

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
    if not sympify(quantity).atoms(Quantity) or not \
            convert_to(quantity, [meter, kilogram, second]).atoms(Quantity):
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

    unit = _format_unit(array[0], desired_unit)

    if len(array) > 4:
        array = [*[_format_number(element, desired_unit) for element in array[:2]],
                 '\\vdots',
                 _format_number(array[-1], desired_unit)]
    else:
        array = [_format_number(element, desired_unit) for element in array]

    number = ('\\left[\\begin{matrix}'
              + '\\\\'.join(array)
              + '\\end{matrix}\\right]')

    return f'{number}{unit}'


def _format_big_matrix(matrix, desired_unit):
    '''look above'''

    matrix = matrix[:, :2].row_join(matrix[:, -1])  # make narrow
    matrix = matrix[:2, :].col_join(matrix[-1, :])  # shorten
    mat_ls = []

    for index in range(matrix[:2, :].rows):
        mat_ls.append(' & '.join(
            [*[_format_number(element, desired_unit) for element in matrix[index, :-1]],
             '\\cdots',
             _format_number(matrix[index, -1], desired_unit)]))

    mat_ls.append(' & '.join(
        [*['\\vdots'] * (matrix.cols - 1), '\\ddots', '\\vdots']))
    mat_ls.append(' & '.join(
        [*[_format_number(element, desired_unit) for element in matrix[-1, :-1]],
         '\\cdots',
         _format_number(matrix[-1, -1], desired_unit)]))

    number = ('\\left[\\begin{matrix}' +
              '\\\\'.join(mat_ls) +
              '\\end{matrix}\\right]')

    return number


def _format_wide_matrix(matrix, desired_unit):
    '''look above'''

    matrix = matrix[:, :2].row_join(matrix[:, -1])  # make narrow
    mat_ls = []
    for index in range(matrix.rows):
        mat_ls.append(' & '.join(
            [*[_format_number(element, desired_unit) for element in matrix[index, :-1]],
             '\\cdots',
             _format_number(matrix[index, -1], desired_unit)]))

    number = ('\\left[\\begin{matrix}' +
              '\\\\'.join(mat_ls) +
              '\\end{matrix}\\right]')

    return number


def _format_long_matrix(matrix, desired_unit):
    '''look above'''

    matrix = matrix[:2, :].col_join(matrix[-1, :])  # shorten
    mat_ls = []
    for index in range(matrix[:2, :].rows):
        mat_ls.append(' & '.join(
            [_format_number(element, desired_unit) for element in matrix[index, :]]))
    mat_ls.append(' & '.join(['\\vdots'] * matrix.cols))
    mat_ls.append(' & '.join(
        [_format_number(element, desired_unit) for element in matrix[-1, :]]))

    number = ('\\left[\\begin{matrix}' +
              '\\\\'.join(mat_ls) +
              '\\end{matrix}\\right]')

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


def format_quantity(quantity, desired_unit=(meter, kilogram, second)):
    '''returns a nicely latex formatted string of the quantity
    including the units (if any)'''

    quantity_type = str(type(quantity))

    if 'array' in quantity_type or 'Array' in quantity_type:
        formatted = _format_array(quantity, desired_unit)

    elif 'matrix' in quantity_type or 'Matrix' in quantity_type:
        formatted = _format_matrix(quantity, desired_unit)

    else:
        number = _format_number(quantity, desired_unit)
        unit = _format_unit(quantity, desired_unit)
        formatted = f'{number}{unit}'

    return formatted


class _calculation:
    '''the calculation entity'''

    def __init__(self, equation):
        '''prepare common variables for subsequent operations'''

        self.main_variable = equation.split('=')[0].strip()
        self.variable_lx = latex(sympify(self.main_variable))
        self.expr_0_str = equation.split('=')[1].strip()
        self.str_exp = re.sub(r'[a-zA-Z_.]*\.([a-zA-Z_]*)',
                              r'\1', self.expr_0_str)
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
        values_list = [__main__.__dict__[str(var)]
                       for var in free_symbols]
        values_dict = dict(zip(variables_list, values_list))
        expr_2_lx = latex(self.sympified, mul_symbol='times')
        for var, val in values_dict.items():
            val_lx = format_quantity(val)
            expr_2_lx = re.sub(
                fr'(?<!_{{|[a-zA-Z_]{{2}}){re.escape(var)}\^?(?![a-zA-Z_]+)',
                lambda mo: (fr'\left({val_lx}\right)^'
                           if mo.group().endswith('^')
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

        if result_unit == (meter, kilogram, second):
            main_value = self.expr_0_str
        else:
            try:
                main_value = convert_to(eval(self.expr_0_str,
                                             __main__.__dict__),
                                        result_unit)
            except:  # if it cannot be converted
                main_value = self.expr_0_str

        exec(f'{self.main_variable} = {main_value}', __main__.__dict__)


def cal(equation, intent='full', unit=(meter, kilogram, second)):
    '''
    evaluate all the calculations, carry out the appropriate assignments,
    and return all the procedures
    (which can be inserted in a pweave or pythontex document with print())

    >>> cal('t_f = 56', 'd')
    $t_{f} = 56$

    >>> print(cal('r_d = sqrt(t_f/56)+78'))
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
        output = eqn(calc.variable_lx + ' = ' + calc.step_one(),
                     norm=False, disp=False)

    elif intent in ('2step', '2'):
        output = eqn(calc.variable_lx + '\t= ' + calc.step_one(),
                     _alignment_tabs * '\t' + '\t= ' + calc.step_three(unit),
                     norm=False, disp=True)

    elif intent in ('last', 'l'):
        output = eqn(calc.variable_lx + '\t= ' + calc.step_three(unit),
                     norm=False, disp=True)

    else:
        output = eqn(calc.variable_lx + '\t= ' + calc.step_one(),
                     _alignment_tabs * '\t' + '\t= ' + calc.step_two(),
                     _alignment_tabs * '\t' + '\t= ' + calc.step_three(unit),
                     norm=False, disp=True)

    return output


def fmt(quantity, unit=(meter, kilogram, second)):
    '''when just formatting is needed'''

    return _surround_equation(format_quantity(quantity, unit), disp=False)
