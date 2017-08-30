# -*- encoding: utf-8 -*-
import json
from copy import deepcopy
from lxml import etree
from os.path import basename
import re
import sys

__author__ = 'tla'

# IDTAG = '{http://www.w3.org/XML/1998/namespace}id'   # xml:id; useful for debugging


def from_file(xmlfile, milestone=None, first_layer=False, normalisation=None, encoding='utf-8'):
    with open(xmlfile, encoding=encoding) as fh:
        return from_fh(fh, milestone=milestone, first_layer=first_layer, normalisation=normalisation)


def from_fh(xml_fh, milestone=None, first_layer=False, normalisation=None):
    xmldoc = etree.parse(xml_fh)            # returns an ETree
    return from_etree(xmldoc, milestone=milestone, first_layer=first_layer, normalisation=normalisation)


def from_string(xml_string, milestone=None, first_layer=False, normalisation=None):
    xmldoc = etree.fromstring(xml_string)   # returns an Element
    return from_element(xmldoc, milestone=milestone, first_layer=first_layer, normalisation=normalisation)


def from_etree(xml_doc, milestone=None, first_layer=False, normalisation=None):
    return from_element(xml_doc.getroot(), milestone=milestone, first_layer=first_layer, normalisation=normalisation)


def from_element(xml_object, milestone=None, first_layer=False, normalisation=None):
    """Take a TEI XML file as input, and return a JSON structure suitable
    for passing to CollateX. Options include:

    * milestone: Restrict the output to text between the given milestone number and the next.
    * first_layer: Instead of using the final layer (e.g. <add> tags, use the first (a.c.)
      layer of the text.
    * normalisation: A function that takes a token and rewrites that token's normalised form,
      if desired."""
    ns = {'t': 'http://www.tei-c.org/ns/1.0'}
    thetext = xml_object.xpath('//t:text', namespaces=ns)[0]
    tokens = []

    if milestone is not None:
        # We will thin out the XML tree to include only those elements
        # between the selected milestone and the next.
        # Make a copy of thetext, so that we don't clobber xmlobject.
        usetext = deepcopy(thetext)
        # Find all the content starting from the given milestone up to
        # the next milestone of the same unit.
        try:
            msel = usetext.xpath('.//t:milestone[@n="%s"]' % milestone, namespaces=ns)[0]
        except IndexError:
            return tokens

        xpathexpr = './following::t:milestone[@unit="%s"]' % (msel.get('unit'))
        nextmsel = msel.xpath(xpathexpr, namespaces=ns)
        # Now we want to remove all the preceding non-parent elements from the block
        # that occur before msel and after msend.
        for prior_el in msel.xpath('./preceding::*'):
            prior_el.clear()
            if prior_el.getparent() is not None:
                prior_el.getparent().remove(prior_el)
        if len(nextmsel):
            msend = nextmsel[0]
            # Clear out all following elements
            for next_el in msend.xpath('./following::*'):
                next_el.clear()
                if next_el.getparent() is not None:
                    next_el.getparent().remove(next_el)
            # Clear out the text tails of ancestor elements up to
            # the original milestone level
            for ancestor in reversed(msend.xpath('./ancestor::*')):
                if msel in ancestor:
                    break
                ancestor.tail = None
            msend.getparent().remove(msend)
        thetext = usetext

    # For each section-like block remaining in the text, break it up into words.
    blocks = thetext.xpath('.//t:div | .//t:ab', namespaces=ns)
    for block in blocks:
        tokens.extend(_find_words(block, first_layer))

    # Now go through all the tokens and apply our function, if any, to normalise
    # the token.
    if normalisation is not None:
        [normalisation(t) for t in tokens]

    return tokens


def _find_words(element, first_layer=False):
    """Detect word boundaries and add an anchor to each."""
    tokens = []
    # First handle the text of the element, if any
    if element.tag is not etree.Comment and element.text is not None:
        _split_text_node(element.text, tokens)

    # Now tokens has only the tokenized contents of the element itself.
    # If there is a single token, then we 'lit' the entire element.
    if len(tokens) == 1:
        tokens[0]['lit'] = etree.tostring(element, encoding='unicode', with_tail=False)

    # Next handle the child elements of this one, if any.
    for child in element:
        child_tokens = _find_words(child, first_layer)
        if len(child_tokens) == 0:
            continue
        if len(tokens) and 'INCOMPLETE' in tokens[-1]:
            # Combine the last of these with the first child token.
            prior = tokens[-1]
            partial = child_tokens.pop(0)
            prior['t'] += partial['t']
            prior['n'] += partial['n']
            # Now figure out 'lit'. Did the child have children?
            if child.text is None and len(child) == 0:
                # It's a milestone element. Stick it into 'lit'.
                prior['lit'] += etree.tostring(child, encoding='unicode', with_tail=False)
            prior['lit'] += partial['lit']
            if 'INCOMPLETE' not in partial:
                del prior['INCOMPLETE']
        # Add the remaining tokens onto our list.
        tokens.extend(child_tokens)

    # Now we handle our tag-specific logic, after the child text and child tags
    # have been processed but before the tail is processed.
    if (_tag_is(element, 'del') and first_layer is False) \
            or (_tag_is(element, 'add') and first_layer is True) or _tag_is(element, 'note'):
        # If we are looking at a del tag for the final layer, or an add tag for the
        # first layer, discard all the tokens we just got, replacing them with an empty
        # token that carries the correct 'incomplete' setting.
        if len(tokens):
            final = tokens[-1]
            tokens = [{'t': '', 'n': '', 'lit': final['lit']}]
            if 'INCOMPLETE' in final:
                tokens[0]['INCOMPLETE'] = True
    elif _tag_is(element, 'abbr'):
        # Mark a sort of regular expression in the token data, for matching.
        if len(tokens) > 0:
            tokens[0]['re'] = '.*%s.*' % '.*'.join(tokens[0]['t'])
    elif _tag_is(element, 'num'):
        # Combine all the word tokens into a single one, and set 'n' to the number value.
        mytoken = {'n': element.get('value'),
                   't': ' '.join([x['t'] for x in tokens]),
                   'lit': ' '.join([x['lit'] for x in tokens])}
        if 'INCOMPLETE' in tokens[-1]:
            mytoken['INCOMPLETE'] = True
        tokens = [mytoken]

    # Finally handle the tail text of this element, if any.
    if element.tail is not None:
        # Strip any insignificant whitespace from the tail.
        tnode = element.tail
        if re.match('.*\}[clp]b$', str(element.tag)):
            tnode = re.sub('^[\s\n]*', '', element.tail, re.S)
        if tnode != '':
            _split_text_node(tnode, tokens)

    # Get rid of any final empty tokens.
    if len(tokens) and _is_blank(tokens[-1]):
        tokens.pop()
    return tokens


def _split_text_node(tnode, tokens):
    tnode = tnode.rstrip('\n')
    words = re.split('\s+', tnode)
    for word in words:
        if len(tokens) and 'INCOMPLETE' in tokens[-1]:
            open_token = tokens.pop()
            open_token['t'] += word
            open_token['n'] += word
            open_token['lit'] += word
            del open_token['INCOMPLETE']
            if not _is_blank(open_token):
                tokens.append(open_token)
        elif word != '':
            token = {'t': word, 'n': word, 'lit': word}
            tokens.append(token)
    if len(tokens) and re.search('\s+$', tnode) is None:
        tokens[-1]['INCOMPLETE'] = True
    return tokens


def _tag_is(el, tag):
    return el.tag == '{http://www.tei-c.org/ns/1.0}%s' % tag


def _is_blank(token):
    if token['n'] != '':
        return False
    if token['t'] != '':
        return False
    # if token['lit'] != '':
    #     return False
    return True


if __name__ == '__main__':
    witness_array = []
    textms = None
    xmlfiles = None
    if re.match('.*\.xml$', sys.argv[1]) is None:
        textms = sys.argv[1]
        xmlfiles = sys.argv[2:]
    else:
        xmlfiles = sys.argv[1:]
    for fn in xmlfiles:
        sigil = re.sub('\.xml$', '', basename(fn))
        result = from_file(fn, textms)
        if len(result):
            witness_array.append({'id': sigil, 'tokens': result})
    result = json.dumps({'witnesses': witness_array}, ensure_ascii=False)
    sys.stdout.buffer.write(result.encode('utf-8'))
