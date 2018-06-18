from sys import path
path.append('..')
# pylint: disable=E0611, E0602
from scirep import document, sqrt
# pylint: enable=E0611

from sympy.physics.units import centimeter, meter, second, mega, newton, pascal, Quantity, pressure, millimeter, length
import numpy as np
import sympy as sp
with document() as a:
    a.section('Design Analysis')
    a.append('The full assembly illustration is shown below.')
    a.subsection('Blade Thickness')
    a.append('Assuming the angle that the "cement bumps" make with the vertical is $30^\\circ$,')
    a.append('And from \\cite[Figure 9.10]{shigley}, the force that a human can exert with one hand vertically down is between 80 N and 116 N. Since two people will pull the blade down with one hand each, the total verticalforce exerted on the blade will be the addition of these forces.')
    a.aserar('F_B = 80*newton + 116*newton', 'final', newton)
    a.append('Then the cement will react with the same force distributed evenly along the blade. Since the blade has a length of  , the vertical reaction of the cement will be:')
    a.aserar('R_c = F_B/(1*meter)', unit = newton/meter)
    a.append('Since the blade will be supported on both ends, from \\cite[Table A-9]{shigley}, it can be assumed as number 7, simple supports, uniform load system. then taking the dimension ')
    a.aserar('b=10*centimeter', 'define')
    a.append(', the stress equations will be solved for h. The Area moment of inertia for the blade is:', 0)
    a.equation('I = (b*h**3)/12')
    a.append('And the center of mass is:')
    a.equation('c = h/2')
    a.append('From \\cite[Table A-9]{shigley}, 7, The maximum bending moment equation can be found, then from that equation, h can be solved for.')
    a.aserar('l = 1*meter', 'final')
    a.aserar('x = l/2')
    a.aserar('M_B = (R_c*x)/2*(l-x)', unit =  newton*meter)
    a.append('The blade material is [Table A21] steel AISI 1040 Q\\&T $205^\\circ C$ that has a tensile strength')
    MPa = Quantity('MPa', pressure, mega*pascal)
    a.aserar('S_B = 779*MPa', 'final', unit=MPa)
    a.append('Taking a factor of safety of:')
    a.aserar('n = 2', 'final')
    a.append('The Thicakess of the blade can now be solved from:')
    eqn = 'S_B/n=M_B*c/I'
    a.equation(eqn)
    a.append('where')
    I = '(b*h**3)/12'
    a.equation(f'I={I}')
    c = 'h/2'
    a.equation(f'c = {c}')
    t_b = a.solve(f'S_B/n-M_B*({c})/({I})', 'h')
    a.aserar(f't_b = {t_b[1]}', unit = millimeter)
    a.append('Therefore the selected thickness of the blade is:')
    a.aserar('t_b = 2.5*millimeter', unit = millimeter)
    a.section('Side Rails')
    a.append('The side rails are made of aluminum for easy removal of dry cement which can obstruct the movement of the blade wheels. The selected aluminum [Table A24] is wrought, 2024, T3 tempered with a strength of ')
    a.aserar('S_Al = 482*MPa', 'final', unit = MPa)
    a.append('The profile of the rails can be approximated as')
    a.figure('profile.png')
    a.append('where ')
    a.aserar('b = 5*centimeter', 'define', millimeter)
    a.append('and ', 0)
    a.aserar('h_ = 11*centimeter', 'define', millimeter)
    a.append('Then the thickness t must be found. The initial guess for the thickness is', 0)
    a.aserar('t = 1*millimeter', 'define', unit = millimeter)
    a.append('The center of mass is:')
    a.aserar('IR = (b*(h_**3))/12 - ((b-2*t)*(h_-2*t)**3)/12')
    a.aserar('S=l+t')
