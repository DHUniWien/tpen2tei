__author__ = 'tla'

import unittest
import json
from parse import from_sc


class Test (unittest.TestCase):

    tei_ns = 'http://www.tei-c.org/ns/1.0'

    # Our default (and example) list of special characters that might occur as
    # glyph (<g/>) elements. A true list should be passed to the from_sc call.
    # The key is the normalized form; the tuple is (xml:id, description).
    _armenian_glyphs = {
        'աշխարհ': ('asxarh', 'ARMENIAN ASHXARH SYMBOL'),
        'ամենայն': ('amenayn', 'ARMENIAN AMENAYN SYMBOL'),
        'որպէս': ('orpes', 'ARMENIAN ORPES SYMBOL'),
        'երկիր': ('erkir', 'ARMENIAN ERKIR SYMBOL'),
        'երկին': ('erkin', 'ARMENIAN ERKIN SYMBOL'),
        'ընդ': ('und', 'ARMENIAN END SYMBOL'),
        'ըստ': ('ust', 'ARMENIAN EST SYMBOL'),
        'պտ': ('ptlig', 'ARMENIAN PEH-TIWN LIGATURE'),
        'թե': ('techlig', 'ARMENIAN TO-ECH LIGATURE'),
        'թի': ('tinilig', 'ARMENIAN TO-INI LIGATURE'),
        'թէ': ('tehlig', 'ARMENIAN TO-EH LIGATURE'),
        'էս': ('eslig', 'ARMENIAN EH-SEH LIGATURE'),
        'ես': ('echslig', 'ARMENIAN ECH-SEH LIGATURE'),
        'յր': ('yrlig', 'ARMENIAN YI-REH LIGATURE'),
        'զմ': ('zmlig', 'ARMENIAN ZA-MEN LIGATURE'),
        'թգ': ('tglig', 'ARMENIAN TO-GIM LIGATURE'),
        'ա': ('avar', 'ARMENIAN AYB VARIANT'),
        'հ': ('hvar', 'ARMENIAN HO VARIANT'),
        'յ': ('yabove', 'ARMENIAN YI SUPERSCRIPT VARIANT')
    }

    def test_basic(self):
        with open('tests/data/M1731.json', encoding='utf-8') as testfile:
            msdata = json.load(testfile)
        xmltree = from_sc(msdata, special_chars=self._armenian_glyphs)
        self.assertEqual(xmltree.getroot().tag, '{%s}TEI' % self.tei_ns)

    def test_comment(self):
        pass

    def test_glyphs(self):
        pass

    def test_xml_element(self):
        pass

    def test_linebreaks(self):
        pass

    def test_columns(self):
        pass

    def test_functioning_namespace(self):
        pass

    # Correction code for the early conventions
    def test_cert_correction(self):
        pass

    def test_glyph_correction(self):
        pass

    def test_type_to_rend(self):
        pass

    def test_corr_to_subst(self):
        pass