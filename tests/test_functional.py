# $ pytest %f --capture=no
from docal import processor
from docal.document.latex import document as handler_t, syntax as syn_t
from docal.document.word import document as handler_w, syntax as syn_w
from docal.parsers.excel import parse as parse_xl
from docal.parsers.dcl import parse as parse_dcl

calculation = r'''
# some other code
from math import *

# Normal assignment
l = sqrt(3**2 + 5**2)
x = 5 #kg,\\\

# refer the value
x + 23 #3,$

# Value reference inline
# then x is #x and 
# some display equation
#$$ v*x + 34 = d/#x + f(x) * (-1) + c_bar > foo >= roo
# some inline equation
#$ f+x/2=log(sqrt(f/w))

# Function creation
d_foo = lambda x: 8*x

# Calculation refering anything
y= 34*x + d_foo(x)
z = {'x_foo': 4, 5: 'foo'}[5]

#some_tag
# default options

#@ $,\
w = x-log(y)
c = w/4+d_foo(4)
#@

e = exp(log(4))

# after text
'''

def test_word():
    word = handler_w('test/w.docx')
    d = processor(syn_w(), word.tags)
    d.send(calculation)
    word.write(d.contents)

def test_excel():
    tex = handler_t('test/t.tex')
    d = processor(syn_t(), tex.tags)
    calculation = parse_xl('test/e.xlsx')
    d.send(calculation)
    tex.write(d.contents)

def test_dcl():
    tex = handler_t('test/t.tex')
    d = processor(syn_t(), tex.tags)
    d.send(parse_dcl('./dcl-example.json'))
    tex.write(d.contents)

def test_latex():
    tex = handler_t('test/t.tex')
    d = processor(syn_t(), tex.tags)
    d.send(calculation)
    tex.write(d.contents)

