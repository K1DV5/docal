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

	def append(self, content, ws = 2):
		self.content +=  '\n' * ws + content

	def chapter(self, title):
		self.append(f'\n\\chapter{{{title}}}', 1)

	def section(self, title):
		self.append(f'\n\\section{{{title}}}', 1)

	def subsection(self, title):
		self.append(f'\n\\subsection{{{title}}}', 1)

	def subsubsection(self, title):
		self.append(f'\n\\subsubsection{{{title}}}', 1)

	def equation(self, *eqns, inline: bool = False, raw: bool = False):
		if raw == True:
			if len(eqns) == 1:
				if inline == True:
					self.append(f' ${eqns[0]}$ ', 1)
				else:
					self.append(f'\n\\begin{{equation}}\n{eqns[0]}\n\\end{{equation}}', 1)
			else:
				self.append('\n\\begin{align}\n\\begin{split}', 1)
				for eq in eqns:
					self.append(f"{eq.replace('=', '&=')}\\\\", 1)
				self.append('\\end{split}\n\\end{align}', 1)
		
		else:
			if len(eqns) == 1:
				if '=' in eqns[0]:
					eq = eqns[0].split('=')
					eqn = sp.latex(sp.simplify(eq[0])) + '=' + sp.latex(sp.simplify(eq[1]))
					if inline == True:
						self.append(f'${eqn}$', 1)
					else:
						self.append(f'\n\\begin{{equation}}\n{eqn}\n\\end{{equation}}', 1)
				else:
					if inline == True:
						self.append(f'${eqns[0]}$', 1)
					else:
						self.append(f'\n\\begin{{equation}}\n{eqns[0]}\n\\end{{equation}}', 1)
			else:
				self.append('\n\\begin{align}\n\\begin{split}', 1)
				for eqt in eqns:
					if '=' in eqt:
						eq = eqt.split('=')
						try: lhand = sp.latex(sp.sympify(eq[0]))
						except: lhand = ''
						rhand = sp.latex(sp.sympify(eq[1]))
						self.append(f'{lhand} &= {rhand}\\\\', 1)
					else:
						self.append(f'{sp.latex(eqt)}\\\\', 1)
				self.append('\\end{split}\n\\end{align}', 1)

	def aserar(self, eqn, intent = 'full', unit = [meter, kilogram, second]):
		'''
		evaluates all the calculations and assignment needed in the eqn
		and writes all the procedures in the document'''

		def format_quantity(qty, unit_m = [meter, kilogram, second]):
			'''returns a nicely latex formatted string of the quantity
			including the units (if any)'''

			qty_type = str(type(qty))
			abb = {'meter': 'm', 'second': 's', 'inch': 'in', 'kilogram': 'kg', 'pascal': 'Pa', 'newton': 'N'}
			
			fmt_un_num = lambda Qty: float(Decimal(str(list(convert_to(Qty, unit_m)
			.evalf().as_coefficients_dict().values())[0])) \
			.quantize(Decimal('0.001')).normalize())

			fmt_un_un = lambda Qty:  '\\mathrm{' + sp.latex(list(convert_to(Qty.evalf(), unit_m)
			.as_coefficients_dict().keys())[0], mul_symbol = 'dot') \
			.replace('\\cdot', '\\,') + '}'

			def fmt_ul(Qty):
				try: return Decimal(str(Qty)) \
				.quantize(Decimal('0.001')).normalize()
				except: return Qty
			
			if 'array' in qty_type or 'Array' in qty_type:
				qty_type = str(type(qty[0]))

				shorten_array = lambda fpart, Ffunc: fpart.replace(
				'\\end{matrix}',
				'\\\\\\vdots\\\\' + 
				str(Ffunc(qty[-1])) + '\\end{matrix}')

				if 'Mul' in qty_type or 'Quantity' in qty_type or 'Pow' in qty_type:
					# array + unit
					if len(qty) < 4:
						# very long array
						number = sp.latex(sp.Matrix(qty).applyfunc(fmt_un_num))
					else:
						# normal length array
						number = shorten_array(sp.latex(sp.Matrix(qty)
						.applyfunc(fmt_un_num)), fmt_un_num)

					un = fmt_un_un(qty[0])

					fmtd = str(number) \
					+ '\\,' \
					+ un.replace('\\frac', '') \
					.replace('}{', '}\\slash{')
					for full_form, short_form in abb.items():
						fmtd = fmtd.replace(full_form, short_form)
					return fmtd

				else:
					# array + num
					if len(qty) < 4:
						return sp.latex(sp.Matrix(qty).applyfunc(fmt_ul))
					else:
						return shorten_array(sp.latex(sp.Matrix(qty[0:2])
						.applyfunc(fmt_ul)), fmt_ul)

			elif 'matrix' in qty_type or 'Matrix' in qty_type:
				qty_type = str(type(qty[0]))

				shrink_matrix = lambda fpart, Ffunc: fpart.replace(
					'\\\\', ' & \\cdots & ' + str(Ffunc(qty[0, -1])) + '\\\\'
					).replace(
					'\\end{matrix}',
					(f' & \\cdots & {Ffunc(qty[1, -1])}'
					'\\\\\\vdots & \\vdots & \\ddots & \\vdots\\\\'
					f'{Ffunc(qty[-1, 0])} & {Ffunc(qty[-1, 1])}'
					f' & \\cdots & {Ffunc(qty[-1, -1])}'
					'\\end{matrix}')
				)

				narrow_matrix = lambda fpart, Ffunc: fpart.replace(
					'\\\\', f' & \\cdots & {Ffunc(qty[0, -1])}\\temp', 1
					).replace(
					'\\\\', f' & \\cdots & {Ffunc(qty[1, -1])}\\temp', 1
					).replace(
					'\\\\', f' & \\cdots & {Ffunc(qty[2, -1])}\\temp', 1
					).replace(
					'\\temp', '\\\\'
					).replace(
					'\\end{matrix}',
					f' & \\cdots & {Ffunc(qty[3, -1])}\\end{{matrix}}'
				)

				shorten_matrix = lambda fpart, Ffunc: fpart.replace(
					'\\end{matrix}',
					('\\\\\\vdots & \\vdots & \\vdots & \\vdots\\\\'
					f'{Ffunc(qty[-1, 0])} & {Ffunc(qty[-1, 1])} & '
					f'{Ffunc(qty[-1, 2])} & {Ffunc(qty[-1, 3])}'
					'\\end{matrix}')
				)

				if 'Mul' in qty_type or 'Quantity' in qty_type or 'Pow' in qty_type:
					# matrix + unit
					if sp.Matrix(qty).rows > 4 and sp.Matrix(qty).cols > 4:
						# very big matrix
						number = shrink_matrix(sp.latex(sp.Matrix(qty[0:2, 0:2])
						.applyfunc(fmt_un_num)), fmt_un_num)
					elif sp.Matrix(qty).rows > 4 and sp.Matrix(qty).cols < 5:
						# very long matrix
						number = shorten_matrix(sp.latex(sp.Matrix(qty[0:2, :])
						.applyfunc(fmt_un_num)), fmt_un_num)
					elif sp.Matrix(qty).rows < 5 and sp.Matrix(qty).cols > 4:
						# very wide matrix
						number = narrow_matrix(sp.latex(sp.Matrix(qty[:, 0:2])
						.applyfunc(fmt_un_num)), fmt_un_num)
					else:
						# normal size matrix
						number = sp.latex(sp.Matrix(qty)
						.applyfunc(fmt_un_num))

					un = fmt_un_un(qty[0, 0])

					fmtd = str(number) \
					+ '\\,' \
					+ un.replace('\\frac', '') \
					.replace('}{', '}\\slash{')
					for full_form, short_form in abb.items():
						fmtd = fmtd.replace(full_form, short_form)
					return fmtd

				else:
					# matrix + num
					if sp.Matrix(qty).rows > 4 and sp.Matrix(qty).cols > 4:
						# very big matrix
						return shrink_matrix(sp.latex(sp.Matrix(qty[0:2, 0:2])
						.applyfunc(fmt_un_num)), fmt_un_num)
					elif sp.Matrix(qty).rows > 4 and sp.Matrix(qty).cols < 5:
						# very long matrix
						return shorten_matrix(sp.latex(sp.Matrix(qty[0:2, :])
						.applyfunc(fmt_un_num)), fmt_un_num)
					elif sp.Matrix(qty).rows < 5 and sp.Matrix(qty).cols > 4:
						# very wide matrix
						return narrow_matrix(sp.latex(sp.Matrix(qty[:, 0:2])
						.applyfunc(fmt_un_num)), fmt_un_num)
					else:
						# normal size matrix
						return sp.latex(sp.Matrix(qty)
						.applyfunc(fmt_un_num))

			else:
				if 'Mul' in qty_type or 'Quantity' in qty_type or 'Pow' in qty_type:
					# single + unit
					number = fmt_un_num(qty)

					un = fmt_un_un(qty)

					fmtd = str(number) \
					+ '\\,' \
					+ un.replace('\\frac', '') \
					.replace('}{', '}\\slash{')
					for full_form, short_form in abb.items():
						fmtd = fmtd.replace(full_form, short_form)
					return fmtd

				else:
					# single + num
					return str(fmt_ul(qty))

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
		expr_2_lx = sp.latex(simplified, mul_symbol = 'times')
		for var, val in values_dict.items():
			expr_2_lx = expr_2_lx.replace(var, str(format_quantity(val)))

		# variable assignment:
		expr_2_str = str(simplified)
		for var in free_symbols:
			expr_2_str = expr_2_str.replace(str(var), '__main__.'+str(var))
		exec(variable_main + '=' + expr_2_str)

		# expression 3:
		expr_3_lx = format_quantity(eval(expr_2_str), unit_m = unit)

		# write equations:
		_tabs_ = len(variable_lx)//4
		if intent == 'define':
			self.equation (
			variable_lx + ' = ' + expr_3_lx,
			inline = True, raw = True)
		elif intent == '2steps' or intent == '2step':
			self.equation (
			variable_lx + '\t= ' + expr_1_lx,
			_tabs_*'\t' + '\t= ' + expr_3_lx,
			raw = True)
		elif intent == 'final':
			self.equation (
			variable_lx + '\t= ' + expr_3_lx,
			raw = True)
		else:
			self.equation (
			variable_lx + '\t= ' + expr_1_lx,
			_tabs_*'\t' + '\t= ' + expr_2_lx,
			_tabs_*'\t' + '\t= ' + expr_3_lx,
			raw = True)

	def figure(self, fig, label = '', caption = ''):
		if label == '': label = fig.split('.')[0]
		if caption != '':
			self.append(
				'\\begin{figure}'
				'\n\\centering\n\\includegraphics{'
				f'{fig}'
				'}\n\\caption{'
				f'{caption}'
				'}\n\\label{'
				f'{label}'
				'}\n\\end{figure}'
			)
		else:
			self.append('\\includegraphics{' + fig + '}')

	def __exit__(self, *args):
		# equation handling package
		if '\\begin{align}' in self.content or '\\begin{matrix}' in self.content:
			self.preamble = self.preamble + '\n\\usepackage{amsmath}'
		# figures handling package
		if '\\includegraphics{' in self.content:
			self.preamble = self.preamble + '\n\\usepackage{graphicx}'
		self.content = ('\\documentclass['
		f'{self.options}]{{'
		f'{self.type}}}\n'
		f'{self.preamble}'
		'\n\\begin{document}'
		f"{self.content.replace('_{}', '')}"
		'\n\n\\end{document}')
		with open(self.name + '.tex', 'w') as file:
			file.write(self.content)
		rmtree('__pycache__', ignore_errors = True)
		if self.file != 'tex':
			from subprocess import run
			run(['pandoc', self.name + '.tex', '-o', self.name + '.' + self.file])