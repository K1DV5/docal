# -ipy

import re
from sympy import sympify, latex, Matrix
from sympy.physics.units import meter, second, kilogram, convert_to, Quantity

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

