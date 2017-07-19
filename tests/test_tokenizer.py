__author__ = 'tla'

import unittest

from tpen2tei.parse import from_sc
import tpen2tei.wordtokenize as wordtokenize

from config import config as config
import helpers

class Test (unittest.TestCase):

    def setUp(self):
        self.settings = config()

        self.tei_ns = self.settings['namespaces']['tei']
        self.xml_ns = self.settings['namespaces']['xml']

        self.glyphs = helpers.glyph_struct(self.settings['armenian_glyphs'])

        self.testfiles = self.settings['testfiles']
        msdata = helpers.load_JSON_file(self.testfiles['json'])
        self.testdoc_noglyphs = from_sc(msdata)
        self.testdoc = from_sc (
            msdata,
            special_chars = self.glyphs
        )

    # def setUp(self):
    #     with open('./data/M1731.json', encoding='utf-8') as fh:
    #         jdata = json.load(fh)
    #     self.testdoc = from_sc(jdata)

    def test_simple(self):
        """Test a plain & simple file without special markup beyond line breaks."""
        pass

    def test_glyphs(self):
        """Test the correct detection and rendering of glyphs. The characters in
        the resulting token should be the characters that are the content of the
        g tag. """
        testdata_noglyphs = {'յեգի<g xmlns="http://www.tei-c.org/ns/1.0" ref="#&#x57A;&#x57F;"/>ոս': 'յեգիոս',
                    'յ<g xmlns="http://www.tei-c.org/ns/1.0" ref="&#x561;&#x577;&#x56D;&#x561;&#x580;&#x570;">աշխար</g>հն': 'յաշխարհն',
                    '<g xmlns="http://www.tei-c.org/ns/1.0" ref="asxarh">աշխարհ</g>ին': 'աշխարհին',
                    '<g xmlns="http://www.tei-c.org/ns/1.0" ref="">աշխարհ</g>ին': 'աշխարհին',
                    'ար<g xmlns="http://www.tei-c.org/ns/1.0" ref="">ա</g>պ<lb xmlns="http://www.tei-c.org/ns/1.0" xml:id="l101276841" n="14"/>կաց': 'արապկաց',
                    '<g xmlns="http://www.tei-c.org/ns/1.0" ref="">աշխարհ</g>ն': 'աշխարհն'}

        testdata_glyphs = {'յեգի<g xmlns="http://www.tei-c.org/ns/1.0" ref="#ptlig">պտ</g>ոս': {'token': 'յեգիպտոս', 'occurrence': 1},
                            'յ<g xmlns="http://www.tei-c.org/ns/1.0" ref="#asxarh">աշխար</g>հն': {'token': 'յաշխարհն', 'occurrence': 1},
                            '<g xmlns="http://www.tei-c.org/ns/1.0" ref="#asxarh">աշխարհ</g>ին': {'token': 'աշխարհին', 'occurrence': 2},
                            'ար<g xmlns="http://www.tei-c.org/ns/1.0" ref="#avar">ա</g>պ<lb xmlns="http://www.tei-c.org/ns/1.0" xml:id="l101276841" n="14"/>կաց': {'token': 'արապկաց', 'occurrence': 1},
                            '<g xmlns="http://www.tei-c.org/ns/1.0" ref="#asxarh">աշխարհ</g>ն': {'token': 'աշխարհն', 'occurrence': 1}}

        tokens = wordtokenize.from_etree(self.testdoc_noglyphs)
        # Find the token that has our substitution
        for t in tokens:
            if '<g xmlns="http://www.tei-c.org/ns/1.0" ref="' in t['lit']:
                self.assertIsNotNone(testdata_noglyphs.get(t['lit']), "Error in rendering glyphs (input data not covered by testdata)")
                self.assertTrue(t['t'] == testdata_noglyphs.get(t['lit']), "Error in rendering glyphs")
                del testdata_noglyphs[t['lit']]
        self.assertEqual(len(testdata_noglyphs), 0, "Did not find any test token")

        tokens = wordtokenize.from_etree(self.testdoc)
        # Find the token that has our substitution
        for t in tokens:
            if '<g xmlns="http://www.tei-c.org/ns/1.0" ref="' in t['lit']:
                self.assertIsNotNone(testdata_glyphs.get(t['lit']), "Error in rendering glyphs (input data not covered by testdata)")
                self.assertTrue(t['t'] == testdata_glyphs.get(t['lit'])['token'], "Error in rendering glyphs")
                testdata_glyphs[t['lit']]['occurrence'] -= 1
                if testdata_glyphs[t['lit']]['occurrence'] == 0:
                    del testdata_glyphs[t['lit']]
        self.assertEqual(len(testdata_glyphs), 0, "Did not find any test token")

    def test_substitution(self):
        """Test that the correct words are picked out of a subst tag."""
        tokens = wordtokenize.from_etree(self.testdoc)
        # Find the token that has our substitution
        for t in tokens:
            if t['lit'] != 'դե<add xmlns="http://www.tei-c.org/ns/1.0">ռ</add>ևս':
                continue
            self.assertEqual(t['t'], 'դեռևս')
            break
        else:
            self.assertTrue(False, "Did not find the testing token")

    def test_substitution_layer(self):
        """Test that the first_layer option works correctly."""
        tokens = wordtokenize.from_etree(self.testdoc, first_layer=True)
        # Find the token that has our substitution
        for t in tokens:
            if t['lit'] != 'դե<del xmlns="http://www.tei-c.org/ns/1.0">ղ</del>ևս':
                continue
            self.assertEqual(t['t'], 'դեղևս')
            break
        else:
            self.assertTrue(False, "Did not find the testing token")

    # def test_del_word_boundary(self):
    #     """Test that a strategically placed del doesn't cause erroneous joining of words.
    #     TODO add testing data"""
    #     pass

    # def test_gap(self):
    #     """Test that gaps are handled correctly. At the moment this means that no token
    #     should be generated for a gap."""
    #     pass

    # def test_milestone_element(self):
    #     """Test that milestone elements (not <milestone>, but e.g. <lb/> or <cb/>)
    #      are passed through correctly in the token 'lit' field."""
    #     pass

    def test_milestone_option(self):
    #     """Test that passing a milestone option gives back only the text from the
    #     relevant <milestone/> element to the next one."""
        tokens = wordtokenize.from_etree(self.testdoc, milestone="401")
        self.assertEqual(len(tokens), 132)
        self.assertEqual(tokens[0]['t'], 'Իսկ')
        self.assertEqual(tokens[-1]['t'], 'ժամկի։')

        tokens407 = wordtokenize.from_etree(self.testdoc, milestone="407")
        self.assertEqual(len(tokens407), 76)
        self.assertEqual(tokens407[0]['t'], 'Դարձլ')
        self.assertEqual(tokens407[-1]['t'], 'ուռհայ։')

    # def test_arbitrary_element(self):
    #     """Test that arbitrary tags (e.g. <abbr>) are passed into 'lit' correctly."""
    #     pass

    # def test_file_input(self):
    #     """Make sure we get a result when passing a file path."""
    #     pass

    # def test_fh_input(self):
    #     """Make sure we get a result when passing an open filehandle object."""
    #     pass

    # def test_string_input(self):
    #     """Make sure we get a result when passing a string containing XML."""
    #     pass

    # def test_object_input(self):
    #     """Make sure we get a result when passing an lxml.etree object."""
    #     pass

    def testLegacyTokenization(self):
        """Test with legacy TEI files from 2009, to make sure the tokenizer
        works with them."""
        testfile = self.testfiles['tei_2009']
        with open(self.testfiles['tei_2009_reference'], encoding='utf-8') as rfh:
            rtext = rfh.read()

        reference = rtext.rstrip().split(' ')
        tokens = wordtokenize.from_file(testfile)
        for i, t in enumerate(tokens):
            self.assertEqual(t['t'], reference[i], "Mismatch at index %d: %s - %s" % (i, t, reference[i]))
