# for word file handling
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from xml.dom.minidom import parseString
from zipfile import ZipFile, ZIP_DEFLATED
# for file operations
from shutil import move, rmtree
# for access to resource template
from importlib.resources import files
# for temp directory
import tempfile
# for path manips
from os import path
# for regex
import re
# log info
import logging
# tag pattern
from ..processing import PATTERN

logger = logging.getLogger(__name__)

DEFAULT_FILE = 'Untitled.docx'

GREEK_LETTERS = {
    'alpha':      'α',
    'nu':         'ν',
    'beta':       'β',
    'xi':         'ξ',
    'Xi':         'Ξ',
    'gamma':      'γ',
    'Gamma':      'Γ',
    'delta':      'δ',
    'Delta':      '∆',
    'pi':         'π',
    'Pi':         'Π',
    'epsilon':    'ϵ',
    'varepsilon': 'ε',
    'rho':        'ρ',
    'varrho':     'ϱ',
    'zeta':       'ζ',
    'sigma':      'σ',
    'Sigma':      'Σ',
    'eta':        'η',
    'tau':        'τ',
    'theta':      'θ',
    'vartheta':   'ϑ',
    'Theta':      'Θ',
    'upsilon':    'υ',
    'Upsilon':    'Υ',
    'iota':       'ι',
    'phi':        'φ',
    'varphi':     'ϕ',
    'Phi':        'Φ',
    'kappa':      'κ',
    'chi':        'χ',
    'lambda':     'λ',
    'Lambda':     'Λ',
    'psi':        'ψ',
    'Psi':        'Ψ',
    'mu':         'µ',
    'omega':      'ω',
    'Omega':      'Ω',
    }

MATH_ACCENTS = {
    'hat': '&#x0302;',
    'check': '&#x030C;',
    'breve': '&#x02D8;',
    'acute': '&#x0301;',
    'grave': '&#x0300;',
    'tilde': '&#x0303;',
    'bar': '&#x0304;',
    'vec': '&#x20D7;',
    'dot': '&#x0307;',
    'ddot': '&#x0308;',
    'dddot': '&#x20DB;',
    }

PRIMES = {'prime': "'", '2prime': "''", '3prime': "'''"}


class syntax:

    # things that are transformed, used for units and such
    transformed = {
        'degC': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>C</m:t></m:r>',
        'degF': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>F</m:t></m:r>',
        'deg': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup>',
        'integral': '<m:r><m:t>&#x222B;</m:t></m:r>'
    }

    # some symbols
    minus = '-'
    times = '×'
    div = '÷'
    cdot = '⋅'
    halfsp = '&#8239;'
    neg = '¬'
    gt = '&gt;'
    lt = '&lt;'
    gte = '≥'
    lte = '≤'
    cdots = '⋯'
    vdots = '⋮'
    ddots = '⋱'

    greek_letters = GREEK_LETTERS
    math_accents = MATH_ACCENTS
    primes = PRIMES

    def txt(self, text):
        return f'<m:r><m:t xml:space="preserve">{text}</m:t></m:r>'

    def txt_rom(self, text):
        return f'<m:r><m:rPr><m:nor/></m:rPr><m:t xml:space="preserve">{text}</m:t></m:r>'

    def txt_math(self, text):
        return self.txt_rom(text)

    def sub(self, base, s):
        return f'<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>'

    def sup(self, base, s):
        return f'<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>'

    def rad(self, base):
        return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{base}</m:e></m:rad>'

    def summation(self, base, end):
        return f'<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr><m:sub><m:r><m:t>i=1</m:t></m:r></m:sub><m:sup><m:r><m:t>{end}</m:t></m:r></m:sup><m:e>{base}</m:e></m:nary>'

    def func_name(self, name):
        return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>{name}</m:t></m:r>'

    def frac(self, num, den):
        return f'<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>'

    def math_disp(self, math):
        return f'<m:oMathPara><m:oMath>{math}</m:oMath></m:oMathPara>'

    def math_inln(self, math):
        return f'<m:oMath>{math}</m:oMath>'

    def greek(self, name):
        return self.txt(GREEK_LETTERS[name])

    def accent(self, acc, base):
        return f'<m:acc><m:accPr><m:chr m:val="{MATH_ACCENTS[acc]}"/></m:accPr><m:e>{base}</m:e></m:acc>'

    def prime(self, base, prime):
        return self.sup(base, self.txt(PRIMES[prime]))

    def delmtd(self, contained, kind=0):
        surround = '<m:dPr><m:begChr m:val="{}"/><m:endChr m:val="{}"/></m:dPr>'
        kinds = ['[]', '{}', '⌊⌋']
        form = '<m:d>{}<m:e>{}</m:e></m:d>'
        if kind == 0:
            return form.format('', contained)
        return form.format(surround.format(kinds[kind-1][0], kinds[kind-1][1]), contained)

    def matrix(self, elmts, full=False):
        if full:  # top level, full matrix
            m_form = '<m:m>{}</m:m>'
            rows = ''.join([f'<m:mr><m:e>{e}</m:e></m:mr>' for e in elmts])
            return self.delmtd(m_form.format(rows), 1)
        return '</m:e><m:e>'.join(elmts)

    def eqarray(self, eqns: list):
        form = '<m:eqArr>{}</m:eqArr>'
        line_form = '<m:e>{}</m:e>'
        align_chr = self.txt('&amp;=')
        return form.format(''.join([line_form.format(align_chr.join(eq)) for eq in eqns]))

class document:

    # the xml declaration
    declaration = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'

    # the internal form of the parsed tags for internal use to avoid normal # usage
    tag_alt_form = '#{%s}'

    def __init__(self, infile=None, outfile=None):
        # the tag pattern
        self.pattern = PATTERN
        # temp folder for converted files
        self.temp_dir = tempfile.mkdtemp()
        self.infile = infile
        if infile:
            # input file specified
            tmp_fname = infile
        else:
            # file taken as input file when not explicitly set:
            tmp_fname = DEFAULT_FILE
            infile = files(__name__).joinpath('word.docx')

        with ZipFile(infile, 'r') as zin:
            file_contents = zin.read('word/document.xml')
            tmp_filename_full = path.join(self.temp_dir, path.splitext(path.basename(tmp_fname))[0])
            self.tmp_file = ZipFile(tmp_filename_full, 'w', compression=ZIP_DEFLATED)
            self.tmp_file.comment = zin.comment
            for file in zin.namelist():
                if file != 'word/document.xml':
                    self.tmp_file.writestr(file, zin.read(file))

        # extract always required namespaces
        self.namespaces = {}
        minidoc = parseString(file_contents)
        for k, v in minidoc.documentElement.attributes.items():
            if not k.startswith('xmlns:'):
                continue
            self.namespaces[k.replace('xmlns:', '', count=1)] = v

        # the xml tree representation of the document contents
        self.doc_tree = ET.fromstring(file_contents)
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

        # the tags in the document (stores tags, their addresses, and whether inline)
        self.tags_info = self.extract_tags_info(self.doc_tree)
        self.tags = [info['tag'] for info in self.tags_info]

        if outfile:
            self.outfile = path.abspath(outfile) 
        elif self.infile:
            base, ext = path.splitext(self.infile)
            self.outfile = base + '-out' + ext
        else:
            self.outfile = DEFAULT_FILE

    def normalized_contents(self, paragraph):
        pref_w = f'{{{self.namespaces["w"]}}}'
        ignored = [pref_w + tag for tag in ['bookmarkStart', 'bookmarkEnd', 'proofErr']]
        conts = []
        for child in paragraph:
            if child.tag == pref_w + 'r':
                if conts:
                    if type(conts[-1]) == list:
                        conts[-1].append(child)
                    else:
                        conts.append(['', child])
                else:
                    conts.append(['', child])
                for t in child:
                    if t.tag == pref_w + 't':
                        conts[-1][0] += t.text
            elif conts and type(conts[-1]) != list or child.tag not in ignored:
                conts.append(child)
        return conts

    def extract_tags_info(self, tree):

        pref_w = f'{{{self.namespaces["w"]}}}'
        tags_info = []
        for index, child in enumerate(tree[0]):
            if child.tag == pref_w + 'p':
                # get its contents and clear it
                conts = self.normalized_contents(child)
                child.clear()
                for cont in conts:
                    if type(cont) == list:
                        if '#' in cont[0]:
                            # replace with a new element
                            w_r = ET.SubElement(child, pref_w + 'r')
                            w_t = ET.SubElement(w_r, pref_w + 't',
                                                {'xml:space': 'preserve'})
                            # store full info about the tags inside
                            for tag in self.pattern.finditer(cont[0]):
                                if cont[0].strip() == '#' + tag.group(2):
                                    position = 'para'
                                else:
                                    position = 'inline'
                                tags_info.append({
                                    'tag': tag.group(2),
                                    'tag-alt': self.tag_alt_form % tag.group(2),
                                    'address': [child, w_r, w_t],
                                    'position': position,
                                    'index': index})
                            # remove \'s from the escaped #'s and change the tags form
                            w_t.text = (re.sub(r'\\#', '#', self.pattern.sub(
                                lambda tag:
                                    tag.group(1) +
                                    self.tag_alt_form % tag.group(2) +
                                    tag.group(3),
                                cont[0])))
                        else:  # preserve properties
                            for r in cont[1:]:
                                child.append(r)
                    else:
                        child.append(cont)

        return tags_info

    def _subs_tags(self, values={}):
        ans_info = {tag: self.para_elts(val) for tag, val in values.items()}

        added = 0  # the added index to make up for the added elements
        for tag, ans_parts in ans_info.items():
            matching_infos = [
                info for info in self.tags_info if info['tag'] == tag]
            if matching_infos:
                info = matching_infos[0]
                # remove this entry to revert the left ones from their alt form
                self.tags_info.remove(info)
                if info['position'] == 'para':
                    ans_parts.reverse()  # because they are inserted at the same index
                    for ans in ans_parts:
                        self.doc_tree[0].insert(info['index'] + added, ans)
                    self.doc_tree[0].remove(info['address'][0])
                    added += len(ans_parts) - 1  # minus the tag para (removed)
                else:
                    loc_para, loc_run, loc_text = info['address']
                    split_text = loc_text.text.split(info['tag-alt'], 1)
                    loc_text.text = split_text[1]
                    index_run = list(loc_para).index(loc_run)
                    pref_w = f'{{{self.namespaces["w"]}}}'
                    # if there is only one para, insert its contents into the para
                    if len(ans_parts) == 1:
                        ans_runs = list(ans_parts[0])
                        ans_runs.reverse()  # same reason as above
                        for run in ans_runs:
                            loc_para.insert(index_run, run)
                        beg_run = ET.Element(pref_w + 'r')
                        beg_text = ET.SubElement(beg_run, pref_w + 't',
                                                 {'xml:space': 'preserve'})
                        beg_text.text = split_text[0]
                        loc_para.insert(index_run, beg_run)
                    else:  # split the para and make new paras between the splits
                        beg_para = ET.Element(pref_w + 'p')
                        beg_run = ET.SubElement(beg_para, pref_w + 'r')
                        beg_text = ET.SubElement(beg_run, pref_w + 't',
                                                 {'xml:space': 'preserve'})
                        beg_text.text = split_text[0]
                        ans_parts.reverse()  # same reason as above
                        for ans in ans_parts:
                            self.doc_tree[0].insert(info['index'] + added, ans)
                        beg_index = info['index'] + added
                        self.doc_tree[0].insert(beg_index, beg_para)
                        added += len(ans_parts) + 1
            else:
                logger.warning(f'#{tag} not found in the document.')
        # revert the rest of the tags from their alt form
        for info in self.tags_info:
            logger.warning(f'There is nothing to send to #{info["tag"]}.')
            loc_text = info['address'][2]
            loc_text.text = loc_text.text.replace(
                info['tag-alt'], '#' + info['tag'])

    def collect_txt(self, content):
        paras = []
        para = [['text', '']]
        for cont in content:
            # so that it has a space before the inline eqn
            space = '' if para[-1][1].endswith(' ') or not para[-1][1] else ' '
            if para[-1][0] == 'text':
                if cont[0] == 'text':
                    if cont[1].strip():
                        para[-1][1] += space + escape(cont[1])
                    elif para[-1][1].strip():
                        paras.append(para)
                        para = [['text', '']]
                else:
                    if cont[0] == 'inline':
                        if para[-1][1].strip():
                            para[-1][1] += space
                        para.append(cont)
                    else:
                        if para[0][1].strip() or len(para) > 1:
                            paras.append(para)
                            para = [['text', '']]
                        paras.append([cont])
            else:
                if cont[0] == 'inline':
                    para.append(['text', space])
                    para.append(cont)
                elif cont[0] == 'text':
                    if cont[1].strip():
                        para.append(['text', space + escape(cont[1])])
                    elif len(para) > 1 or para[0][1].strip():
                        paras.append(para)
                        para = [['text', '']]
                else:
                    if para[0][1].strip() or len(para) > 1:
                        paras.append(para)
                        para = [['text', '']]
                    paras.append([cont])
        if para[0][1].strip() or len(para) > 1:
            paras.append(para)
        return paras

    def para_elts(self, content: list):
        w = self.namespaces['w']
        m = self.namespaces['m']
        para_start = f'<w:p xmlns:w="{w}" xmlns:m="{m}">'
        para_form = para_start + '{}</w:p>'
        run_form = '<w:r><w:t xml:space="preserve">{}</w:t></w:r>'
        paras = []
        for para in self.collect_txt(content):
            para_xml_ls = []
            for part in para:
                if part[0] == 'text':
                    if part[1].strip():
                        para_xml_ls.append(run_form.format(part[1]))
                else:
                    para_xml_ls.append(part[1])
            para_xml = para_form.format(''.join(para_xml_ls))
            paras.append(ET.fromstring(para_xml))

        return paras

    def write(self, values={}):
        if self.infile:
            self._subs_tags(values)
        else:
            for child in self.doc_tree[0]:
                self.doc_tree[0].remove(child)
            for val in values.values():
                for para in self.para_elts(val):
                    self.doc_tree[0].append(para)
        # take care of namespaces and declaration
        doc_xml = ET.tostring(self.doc_tree, encoding='unicode')
        searched = re.match(r'\<w:document.*?\>', doc_xml).group(0)
        used_nses = re.findall(r'(?<=xmlns\:)\w+', searched)
        for prefix, uri in self.namespaces.items():
            if prefix not in used_nses:
                self.doc_tree.set('xmlns:' + prefix, uri)

        doc_xml = self.declaration + \
            ET.tostring(self.doc_tree, encoding='unicode')
        self.tmp_file.writestr('word/document.xml', doc_xml)
        tmp_filename = self.tmp_file.filename
        self.tmp_file.close()

        logger.info('[writing file] %s', self.outfile)
        move(tmp_filename, self.outfile)

        rmtree(self.temp_dir)


