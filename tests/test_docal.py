'test docal'
import sys

sys.path.append('..')
import src
from os import path
from subprocess import run
from docal import document, parsing
from docal.document import calculations

syn_l = parsing.SyntaxLatex()

def test_document():
    assert type(document) == type

def test_fit_matrix():
    syn_obj = parsing.SyntaxLatex()
    fit = parsing._fit_matrix
    short = [1,2,3,4,5]
    long = [1,2,3,4,5,6,7,8,9,10,11,12,13]
    assert fit(short, syn_obj) == short
    assert fit(long, syn_obj) == long[:8] + [syn_obj.vdots] + [long[-1]]

def test_latexify():
    theta = [x*360/11 for x in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]] #3, deg, $, m12
    # , and
    V_out = [0.01, 0.02, 1.63, 2.44, 3.25, 4.07, 4.88, 5.69, 6.51, 7.32, 8.19] #V, $, 3, m12

    # Using the least squares regression, the coefficients can be found as:
    n = len(V_out) #3
    Sigma_XiYi = sum([x*y for x, y in zip(theta, V_out)]) #3
    Sigma_0xi = sum(theta) #3
    Sigma_yi = sum(V_out) #3
    Sigma_xi2 = sum([x**2 for x in theta]) #3
    x_bar = sum(theta)/n #3
    y_bar = sum(V_out)/n #3
    proc = calculations([], 'latex', locals()).process
    out = proc('a_1 = (n*Sigma_XiYi - Sigma_0xi*Sigma_yi) / (n*Sigma_xi2 - Sigma_0xi**2)')
    with open('tex/t.tex') as file:
        template = file.read()
    with open('tex/tt.tex', 'w') as file:
        file.write(template.replace('#eqn', out[0][1][1]))
    tex_path = path.join(path.dirname(path.abspath(__file__)), 'tex/tt.tex')
    run(['python', 'D:/Documents/Code/.dotfiles/misc/do.py', tex_path])

test_latexify()
