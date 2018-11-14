# -ipy

import re

def _format_number(number):
    '''make the number part of a quantity more readable'''

    if number > 1000 or number < 0.1:
        # in scientific notation
        number = re.sub(r'([0-9]+)E([-+])([0-9]+)',
                        r'\1\\left(10^{\2'+r'\g<3>'.lstrip(r'0')+r'}\\right)',
                        f'{number:.2E}').replace('+', '')
    else:
        if number == int(number):
            number = str(int(number))
        else:
            number = str(round(number, 3))

    return number


def _format_array(array):
    '''look above'''

    if len(array) > 4:
        array = [*[_format_number(element) for element in array[:2]],
                 '\\vdots',
                 _format_number(array[-1])]
    else:
        array = [_format_number(element) for element in array]

    number = ('\\left[\\begin{matrix}'
              + '\\\\'.join(array)
              + '\\end{matrix}\\right]')

    return f'{number}'


def _format_big_matrix(matrix):
    '''look above'''

    cut_matrix = matrix[:2, :2].tolist()
    last_col = matrix[:2, -1].tolist()
    last_row = matrix[-1, :2].tolist()
    last_element = matrix[-1,-1]

    mat_ls = [' & '.join(
        [_format_number(element) for element in cut_matrix[index]]) + ' & \\cdots & ' + _format_number(last_col[index][0])
        for index in range(len(cut_matrix))] \
        + [' & '.join(['\\vdots'] * 2 + ['\\ddots', '\\vdots'])] \
        + [' & '.join([_format_number(element) for element in last_row[0]]) + ' & \\cdots & ' + _format_number(last_element)]

    return mat_ls


def _format_wide_matrix(matrix):
    '''look above'''

    cut_matrix = matrix[:, :2].tolist()
    last_col = matrix[:, -1].tolist()

    mat_ls = [' & '.join(
        [_format_number(element) for element in cut_matrix[index]]) + ' & \\cdots & ' + _format_number(last_col[index][0])
        for index in range(matrix.shape[0])]

    return mat_ls

def _format_long_matrix(matrix):
    '''look above'''

    mat_ls = [' & '.join(
                          [_format_number(element) for element in matrix[:2, :].tolist()[index]])
                          for index in range(matrix[:2, :].shape[0])]
    mat_ls.append(' & '.join(['\\vdots'] * matrix.shape[1]))
    mat_ls.append(' & '.join([_format_number(element) for element in matrix[-1, :].tolist()[0]]))

    return mat_ls


def _format_matrix(matrix):
    '''look above'''

    if matrix.shape[0] > 4 and matrix.shape[1] > 4:
        mat_ls = _format_big_matrix(matrix)
    elif matrix.shape[0] > 4 and matrix.shape[1] < 5:
        mat_ls = _format_long_matrix(matrix)
    elif matrix.shape[0] < 5 and matrix.shape[1] > 4:
        mat_ls = _format_wide_matrix(matrix)
    else:
        mat_ls = [' & '.join(
            [_format_number(element) for element in matrix.tolist()[index]])
            for index in range(matrix.shape[0])]

    number = ('\\left[\\begin{matrix}' +
              '\\\\'.join(mat_ls) +
              '\\end{matrix}\\right]')


    return number

def format_quantity(quantity):
    '''returns a nicely latex formatted string of the quantity
    including the units (if any)'''

    quantity_type = str(type(quantity))

    if 'array' in quantity_type or 'Array' in quantity_type:
        formatted = _format_array(quantity)

    elif 'matrix' in quantity_type:
        formatted = _format_matrix(quantity)

    else:
        number = _format_number(quantity)
        formatted = f'{number}'

    return formatted

