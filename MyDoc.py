from shutil import rmtree
import sympy as sp
from sympy.physics.units import meter, second, kilogram, convert_to
from decimal import Decimal
import __main__

class document:
	'''contains (almost) all of the functionality for a LaTeX document'''

	def __init__(self):
		'''begins writing a document with a default documentclass: article, 11pt
		Note: chapter cannot be used with article'''
		self.name = __main__.__file__.replace('.py', '')
		self.type = 'article'
		self.options = '11pt'
		self.preamble = ''
		self.content = ''
		self.file = 'tex'

	def __enter__(self):
		return self

	def append(self, content, whitespace = 2):
		self.content = self.content + '\n' * whitespace + content

	def chapter(self, title):
		self.append('\n\\chapter{' + title + '}', 1)

	def section(self, title):
		self.append('\n\\section{' + title + '}', 1)

	def subsection(self, title):
		self.append('\n\\subsection{' + title + '}', 1)

	def subsubsection(self, title):
		self.append('\n\\subsubsection{' + title + '}', 1)

	def equation(self, *eqns, inline: bool = False):
		if len(eqns) == 1:
			if inline == True:
				self.append(' $' + eqns[0] + '$ ', 1)
			else:
				self.append('\n\\begin{equation}\n' + eqns[0] + '\n\\end{equation}', 1)
		else:
			self.append('\n\\begin{align}\n\\begin{split}', 1)
			for eq in eqns:
				self.append(eq.replace('=', '&=') +'\\\\', 1)
			self.append('\\end{split}\n\\end{align}', 1)

	def aserar(self, eqn, intent = 'full', unit = [meter, kilogram, second]):
		'''
		evaluates all the calculations and assignment needed in the eqn and writes all the procedures in the document'''

		def format_quantity(qty, unit_m = [meter, kilogram, second]):
			'''returns a nicely latex formatted string of the quantity including the units (if any)'''

			qty_type = str(type(qty))
			try:
				if 'array' in qty_type or 'Array' in qty_type:
					return sp.latex(sp.Matrix(qty)
					.applyfunc(lambda Ray:
					str(Decimal(str(Ray))
					.quantize(Decimal('0.001'))
					.normalize())))
				else:
					return str(Decimal(str(qty))
					.quantize(Decimal('0.001'))
					.normalize())

			except:
				if 'array' in qty_type or 'Array' in qty_type:
					number = sp.latex(sp.Matrix(qty)
					.applyfunc(lambda Ray: 
					Decimal(str(list(convert_to(Ray, unit_m)
					.evalf().as_coefficients_dict().values())[0]))
					.quantize(Decimal('0.001')).normalize()))

					un = '\\mathrm{' \
					+ sp.latex(list(convert_to(qty[0].evalf(), unit_m)
					.as_coefficients_dict().keys())[0], mul_symbol = 'dot') \
					.replace('\\cdot', '\\,') \
					+ '}'

				else:
					number = Decimal(str(list(convert_to(qty, unit_m).evalf()
					.as_coefficients_dict().values())[0])).quantize(Decimal('0.001')) \
					.normalize()

					un = '\\mathrm{' + sp.latex(list(convert_to(qty.evalf(), unit_m)
					.as_coefficients_dict().keys())[0], mul_symbol = 'dot') \
					.replace('\\cdot', '\\,') + '}'

				abb = {'meter': 'm', 'second': 's', 'inch': 'in', 'kilogram': 'kg', 'pascal': 'Pa', 'newton': 'N'}
				fmtd = str(number) \
				+ '\\,' \
				+ un.replace('\\frac', '') \
				.replace('}{', '}\\slash{')
				for full_form, short_form in abb.items():
					fmtd = fmtd.replace(full_form, short_form)
				return fmtd
		# main variable:
		lhand = eqn.split('=')[0].strip()
		variable_main = '__main__.' + lhand
		variable_lx = sp.latex(sp.simplify(lhand))

		# expression 1:
		simplified = sp.simplify(eqn.split('=')[1].strip())
		expr_1_lx = sp.latex(simplified, mul_symbol = 'dot')

		# expression 2:
		free_symbols = list(simplified.atoms(sp.Symbol))
		variables_list = [sp.latex(var) for var in free_symbols]
		values_list = [eval('__main__.' + str(var)) for var in free_symbols]
		values_dict = dict(zip(variables_list, values_list))
		print(values_dict)
		expr_2_str = str(simplified)
		for var in free_symbols:
			expr_2_str = expr_2_str.replace(str(var), '__main__.'+str(var))
		expr_2_lx = sp.latex(simplified, mul_symbol = 'times')
		for var, val in values_dict.items():
			expr_2_lx = expr_2_lx.replace(var, str(format_quantity(val)))

		# expression 3:
		expr_3_lx = format_quantity(simplified.subs(
		dict(zip(free_symbols, values_list))
		), unit_m = unit)

		# variable assignment:
		exec(variable_main + '=' + expr_2_str)

		# output:
		_tabs_ = len(variable_lx)//4
		if intent == 'define':
			self.equation (
			variable_lx + ' = ' + expr_3_lx,
			inline = True)
		elif intent == '2steps' or intent == '2step':
			self.equation (
			variable_lx + '\t= ' + expr_1_lx,
			_tabs_*'\t' + '\t= ' + expr_3_lx)
		else:
			self.equation (
			variable_lx + '\t= ' + expr_1_lx,
			_tabs_*'\t' + '\t= ' + expr_2_lx,
			_tabs_*'\t' + '\t= ' + expr_3_lx)

	def __exit__(self, *args):
		if '\\begin{align}' in self.content: self.preamble = self.preamble + '\n\\usepackage{amsmath}'
		self.content = '\\documentclass[' + self.options + ']{' + self.type + '}' + self.preamble + '\n\\begin{document}' + self.content.replace('_{}', '') + '\n\n\\end{document}'
		with open(self.name + '.tex', 'w') as file:
			file.write(self.content)
		rmtree('__pycache__', ignore_errors = True)
		if self.file != 'tex':
			from subprocess import run
			run(['pandoc', self.name + '.tex', '-o', self.name + '.' + self.file])