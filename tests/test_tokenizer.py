__author__ = 'tla'

import unittest
import wordtokenize


class Test (unittest.TestCase):

    def test_simple(self):
        """Test a plain & simple file without special markup beyond line breaks."""
        pass

    def test_glyphs(self):
        """Test the correct detection and markup of glyphs."""
        pass

    def test_substitution(self):
        """Test that the correct words are picked out of a subst tag."""
        pass

    def test_substitution_layer(self):
        """Test that the first_layer option works correctly."""

    def test_gap(self):
        """Test that gaps are handled correctly."""
        pass

    def test_milestone_element(self):
        """Test that milestone elements are passed through correctly."""
        pass

    def test_milestone_option(self):
        """Test that passing a milestone option gives back only the text to the next milestone."""
        pass

    def test_arbitrary_element(self):
        """Test that arbitrary tags are passed into 'lit' correctly."""
        pass

    def test_file_input(self):
        pass

    def test_fh_input(self):
        pass

    def test_string_input(self):
        pass

    def test_object_input(self):
        pass

    def testLegacyTokenization(self):
        """Test with legacy TEI files from 2009, to make sure the tokenizer
        works with them."""
        testfile = 'tests/data/matenadaran_1896.xml'
        with open('tests/data/matenadaran_1896_reference.txt', encoding='utf-8') as rfh:
            rtext = rfh.read()
        reference = rtext.rstrip().split(' ')
        tokens = wordtokenize.from_file(testfile)
        for i, t in enumerate(tokens):
            self.assertEqual(t['t'], reference[i], "Mismatch at index %d: %s - %s" % (i, t, reference[i]))
