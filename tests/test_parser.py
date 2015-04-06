__author__ = 'tla'

import unittest
import json
from parse import from_sc


class Test (unittest.TestCase):

    tei_ns = 'http://www.tei-c.org/ns/1.0'

    def test_basic(self):
        with open('tests/data/M1731.json', encoding='utf-8') as testfile:
            msdata = json.load(testfile)
        xmltree = from_sc(msdata)
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