from sys import path
path.append('..')
# pylint: disable=E0611, E0602
from scirep import document, sqrt
# pylint: enable=E0611

from sympy.physics.units import centi, meter, second, mega, newton, pascal, Quantity, pressure, milli, length
import numpy as np
import sympy as sp
with document() as a:
	a.section('Design Analysis')
	a.append('The full assembly illustration is shown below.')
	a.subsection('Blade Thickness')
	a.append('Assuming the angle that the "cement bumps" make with the vertical is $30^\\circ$,')
	a.append('And from \\cite[Figure 9.10]{shigley}, the force that a human can exert with one hand vertically down is between 80 N and 116 N. Since two people will pull the blade down with one hand each, the total verticalforce exerted on the blade will be the addition of these forces.')
	a.aserar('F_B = 80*newton + 116*newton', 'final')
	a.append('Then the cement will react with the same force distributed evenly along the blade. Since the blade has a length of  , the vertical reaction of the cement will be:')
	a.aserar('R_c = F_B/(1*meter)', unit = newton/meter)
	a.append('Since the blade will be supported on both ends, from \\cite[Table A-9]{shigley}, it can be assumed as number 7, simple supports, uniform load system. then taking the dimension ')
	cm = centi*meter
	a.aserar('b=10*cm', 'define')
	a.append(', the stress equations will be solved for h. The Area moment of inertia for the blade is:', 0)
	a.equation('I = (b*h**3)/12')
	a.append('And the center of mass is:')
	a.equation('c = h/2')
	a.append('From \\cite[Table A-9]{shigley}, 7, The maximum bending moment equation can be found, then from that equation, h can be solved for.')
	a.aserar('l_ = 1*meter', 'final')
	a.aserar('x = l_/2')
	a.aserar('M_B = (R_c*x)/2*(l_-x)', unit =  newton*meter)
	a.append('The blade material is [Table A21] steel AISI 1040 Q\\&T $205^\\circ C$ that has a tensile strength')
	MPa_ = Quantity('MPa', pressure, mega*pascal)
	a.aserar('S_B = 779*MPa_', 'final', unit = MPa_)
	a.append('Taking a factor of safety of:')
	a.aserar('n = 2', 'final')
	a.append('The Thicakess of the blade can now be solved from:')
	eqn = 'S_B/n=M_B*c/I_'
	a.equation(eqn)
	a.append('where')
	I_ = '(b*h**3)/12'
	a.equation(f'I_={I_}')
	c = 'h/2'
	a.equation(f'c = {c}')
	t_b = a.solve(f'S_B/n-M_B*{c}/{I_}', 'h')
	mm = Quantity('mm', length, milli*meter)
	a.aserar(f't_b = {t_b[1]}', unit = mm)
