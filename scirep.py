from shutil import rmtree
import sympy as sp
from sympy import latex, sympify, Symbol, sqrt, solve, Matrix
from sympy.physics.units import meter, second, kilogram, convert_to, Quantity
import re
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
			lxify = lambda eq: latex(eq, mul_symbol = 'dot')
			if len(eqns) == 1:
				if '=' in eqns[0]:
					eq = eqns[0].split('=')
					eqn = (lxify(sympify(eq[0])).replace('\\cdot', '\\,')
						+ '='
						+ lxify(sympify(eq[1])).replace('\\cdot', '\\,')
					)
					if inline == True:
						self.append(f'${eqn}$', 1)
					else:
						self.append(f'\n\\begin{{equation}}\n{eqn}\n\\end{{equation}}', 1)
				else:
					expr = sympify(eqns[0])
					if inline == True:
						self.append(f'${lxify(expr)}$', 1)
					else:
						self.append(f'\n\\begin{{equation}}\n{lxify(expr)}\n\\end{{equation}}', 1)
			else:
				self.append('\n\\begin{align}\n\\begin{split}', 1)
				for eqt in eqns:
					if '=' in eqt:
						eq = eqt.split('=')
						try: lhand = lxify(sympify(eq[0]))
						except: lhand = ''
						rhand = lxify(sympify(eq[1]))
						self.append(f'{lhand} &= {rhand}\\\\', 1)
					else:
						self.append(f'{lxify(eqt)}\\\\', 1)
				self.append('\\end{split}\n\\end{align}', 1)

	def aserar(self, eqn, intent = 'full', unit = [meter, kilogram, second]):
		'''
		evaluates all the calculations and assignment needed in the eqn
		and writes all the procedures in the document'''

		abb = {'meter': 'm', 'millimeter': 'mm', 'second': 's', 'inch': 'in', 'kilogram': 'kg', 'pascal': 'Pa', 'newton': 'N'}
		def format_quantity(qty, unit_internal = [meter, kilogram, second]):
			'''returns a nicely latex formatted string of the quantity
			including the units (if any)'''

			qty_type = str(type(qty))

			def units_count(Qty):
				try: return len(Qty.atoms(Quantity))
				except: return 0
			
			# re.sub(r'([0-9]*)e([-+][0-9]*)', r'\1\\times 10^{\2}', vb)
			def fmt_un_num(Qty):
				Num = float(list(
				convert_to(Qty, unit_internal)
				.evalf().as_coefficients_dict().values())[0])
				if Num > 1000 or Num < 0.1:
					return re.sub(r'([0-9]*)E([+-][0-9]*)'
					, r'\1(10^{\2})', f'{Num:.2E}')\
					.replace('+', '')
				else:
					if Num == int(Num):
						return str(int(Num))
					else:
						return str(round(Num, 3))

			def fmt_un_un(Qty):
				return '\\mathrm{' \
					+ latex(list(convert_to(Qty.evalf(), unit_internal)
					.as_coefficients_dict().keys())[0], mul_symbol = 'dot') \
					.replace('\\cdot', '\\,') + '}'

			def fmt_ul(Qty):
				if Qty > 1000 or Qty < 0.1:
					return re.sub(r'([0-9]*)E([-+][0-9]*)'
					, r'\1(10^{\2})', f'{Qty:.2E}')\
					.replace('+', '')
				else:
					if Qty == int(Qty):
						return str(int(Qty))
					else:
						return str(round(Qty, 3))

			if 'array' in qty_type or 'Array' in qty_type:

				shorten_array = lambda fpart, Ffunc: fpart.replace(
				'\\end{matrix}',
				f'\\\\\\vdots\\\\{Ffunc(qty[-1])}\\end{{matrix}}')

				def format_array(Qty, Ffunc):
					Arr_lx = latex(Qty)
					for ele in Qty: Arr_lx = Arr_lx.replace(str(ele), Ffunc(ele))
					return Arr_lx

				qty_mat = Matrix(qty)
				if units_count(qty[0]) != 0:
					# array + unit
					if len(qty) < 4:
						# very long array
						number = format_array(qty_mat, fmt_un_num)
					else:
						# normal length array
						number = shorten_array(format_array(qty_mat
						, fmt_un_num), fmt_un_num)

					un = fmt_un_un(qty[0])
					for full_form, short_form in abb.items():
						un = re.sub(fr'(?<=[^a-zA-Z_]){full_form}(?=[^a-zA-Z_])', short_form, un)

					fmtd = number \
					+ '\\,' \
					+ un.replace('\\frac', '') \
					.replace('}{', '}\\slash{')
					return fmtd

				else:
					# array + num
					if len(qty) < 4:
						return latex(Matrix(qty).applyfunc(fmt_ul))
					else:
						return shorten_array(latex(Matrix(qty[0:2])
						.applyfunc(fmt_ul)), fmt_ul)

			elif 'matrix' in qty_type or 'Matrix' in qty_type:

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

				def format_matrix(Mat, Ffunc):
					Mat_lx = latex(Mat)
					for ele in Mat: Mat_lx = Mat_lx.replace(str(ele), f'{Ffunc(ele)}')
					return Mat_lx

				qty_mat = Matrix(qty)
				if units_count(qty[0]) != 0:
					# matrix + unit
					if qty_mat.rows > 4 and qty_mat.cols > 4:
						# very big matrix
						number = shrink_matrix(format_matrix(qty_mat[0:2, 0:2]
						, fmt_un_num), fmt_un_num)
					elif qty_mat.rows > 4 and qty_mat.cols < 5:
						# very long matrix
						number = shorten_matrix(format_matrix(qty_mat[0:2, :]
						, fmt_un_num), fmt_un_num)
					elif qty_mat.rows < 5 and qty_mat.cols > 4:
						# very wide matrix
						number = narrow_matrix(format_matrix(qty_mat[:, 0:2]
						, fmt_un_num), fmt_un_num)
					else:
						# normal size matrix
						number = format_matrix(qty_mat
						, fmt_un_num)

					un = fmt_un_un(qty[0, 0])
					for full_form, short_form in abb.items():
						un = re.sub(fr'(?<=[^a-zA-Z_]){full_form}(?=[^a-zA-Z_])', short_form, un)

					fmtd = str(number) \
					+ '\\,' \
					+ un.replace('\\frac', '') \
					.replace('}{', '}\\slash{')
					return fmtd

				else:
					# matrix + num
					if qty_mat.rows > 4 and qty_mat.cols > 4:
						# very big matrix
						return shrink_matrix(format_matrix(qty_mat[0:2, 0:2]
						, fmt_ul), fmt_ul)
					elif qty_mat.rows > 4 and qty_mat.cols < 5:
						# very long matrix
						return shrink_matrix(format_matrix(qty_mat[0:2, :]
						, fmt_ul), fmt_ul)
					elif qty_mat.rows < 5 and qty_mat.cols > 4:
						# very wide matrix
						return shrink_matrix(format_matrix(qty_mat[:, 0:2]
						, fmt_ul), fmt_ul)
					else:
						# normal size matrix
						return format_matrix(qty_mat, fmt_ul)

			else:
				if units_count(qty) != 0:
					# single + unit
					number = fmt_un_num(qty)
					un = fmt_un_un(qty)
					for full_form, short_form in abb.items():
						un = re.sub(fr'(?<=[^a-zA-Z_]){full_form}(?=[^a-zA-Z_])'
						, short_form, un)

					fmtd = number \
					+ '\\,' \
					+ un.replace('\\frac', '') \
					.replace('}{', '}\\slash{')
					return fmtd

				else:
					# single + num
					return fmt_ul(qty)

		# main variable:
		variable_main = eqn.split('=')[0].strip()
		variable_lx = latex(sympify(variable_main))

		# expression 1:
		sympified = sympify(eqn.split('=')[1].strip())
		expr_1_lx = latex(sympified, mul_symbol = 'dot')
		for full_form, short_form in abb.items():
			if full_form in expr_1_lx:
				expr_1_lx = re.sub(fr'(?<=[^a-zA-Z_]){full_form}(?=[^a-zA-Z_])'
				, f'\\mathrm{{{short_form}}}'
				, expr_1_lx)

		# expression 2:
		free_symbols = list(sympified.atoms(Symbol))
		variables_list = [latex(var) for var in free_symbols]
		values_list = [eval(str(var), __main__.__dict__) for var in free_symbols]
		values_dict = dict(zip(variables_list, values_list))
		expr_2_lx = latex(sympified, mul_symbol = 'times')
		for var, val in values_dict.items():
			expr_2_lx = re.sub(fr'(?<=[^a-zA-Z_]){var}(?=[^a-zA-Z_])',
				format_quantity(val),
				expr_2_lx)

		# variable assignment:
		expr_2_str = str(sympified)
		exec(variable_main + '=' + expr_2_str, __main__.__dict__)

		# expression 3:
		expr_3_lx = format_quantity(eval(expr_2_str, __main__.__dict__),
			unit_internal = unit)

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

	def solve(self, strg, var):
		eqn = sympify(strg)
		var = sympify(var)
		return solve(eqn, var)

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
		post_fixes = {'_{}': '', '\\mathrm{m \\, N}': '\\mathrm{N \\, m}', '^{1.0}': ''}
		for wrng, rght in post_fixes.items():
			self.content = self.content.replace(wrng, rght)
		self.content = ('\\documentclass['
		f'{self.options}]{{'
		f'{self.type}}}\n'
		f'{self.preamble}'
		'\n\\begin{document}'
		f"{self.content}"
		'\n\n\\end{document}')
		with open(self.name + '.tex', 'w') as file:
			file.write(self.content)
		rmtree('__pycache__', ignore_errors = True)
		if self.file != 'tex':
			from subprocess import run
			run(['pandoc', self.name + '.tex', '-o', self.name + '.' + self.file])
