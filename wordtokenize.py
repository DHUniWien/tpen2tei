# -*- encoding: utf-8 -*-
__author__ = 'tla'

import json
from lxml import etree
import re
import sys

IDTAG = '{http://www.w3.org/XML/1998/namespace}id'


def wordtokenize(xmlfile, milestone=None, first_layer=False):
    """Take a TEI XML file as input, and return a JSON structure suitable
    for passing to CollateX."""
    xmldoc = etree.parse(xmlfile).getroot()
    ns = {'t': 'http://www.tei-c.org/ns/1.0'}
    thetext = xmldoc.xpath('//t:text', namespaces=ns)[0]

    # For each paragraph-like block in the text, break it up into words.
    tokens = []
    blocks = thetext.xpath('.//t:p | .//t:ab', namespaces=ns)
    if milestone is not None:
        # Find all the content starting from the given milestone up to
        # the next milestone of the same unit.
        try:
            msel = thetext.xpath('.//t:milestone[@n=%s]' % milestone, namespaces=ns)[0]
        except IndexError:
            return tokens
        xpathexpr = './/t:milestone[@n="%s"]/following-sibling::t:milestone[@unit="%s"]' % (milestone, msel.get('unit'))
        nextmsel = thetext.xpath(xpathexpr, namespaces=ns)
        msend = None
        if len(nextmsel):
            msend = nextmsel[0]
        in_milestone = False
        for block in blocks:
            for el in block.iterchildren():
                if el is msel:
                    in_milestone = True
                elif el is msend:
                    in_milestone = False
                # TODO handle nested milestones
                if not in_milestone:
                    el.getparent().remove(el)
    for block in blocks:
        tokens.extend(_find_words(block, first_layer))

    return tokens


def _find_words(element, first_layer=False):
    """Detect word boundaries and add an anchor to each."""
    tokens = []
    # First handle the text of the element, if any
    if element.text is not None:
        _split_text_node(element.text, tokens)

    # Now tokens has only the tokenized contents of the element itself.
    # If there is a single token, then we 'lit' the entire element.
    if len(tokens) == 1:
        tokens[0]['lit'] = etree.tostring(element, encoding='unicode', with_tail=False)

    # Now we handle our tag-specific logic.
    if _tag_is(element, 'num'):
        # Combine all the word tokens into a single one, and set 'n'.
        mytoken = {'n': element.get('value'),
                   't': ' '.join([x['t'] for x in tokens]),
                   'lit': ' '.join([x['lit'] for x in tokens])}
        if 'INCOMPLETE' in tokens[-1]:
            mytoken['INCOMPLETE'] = True
        tokens = [mytoken]

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
            if child.text is None:
                prior['lit'] += etree.tostring(child, encoding='unicode', with_tail=False)
            prior['lit'] += partial['lit']
            if 'INCOMPLETE' not in partial:
                del prior['INCOMPLETE']
        # Add the remaining tokens onto our list.
        tokens.extend(child_tokens)

    # If we are looking at a del tag for the final layer, or an add tag for the
    # first layer, discard all the tokens we just got and go straight to tail.
    if (_tag_is(element, 'del') and first_layer is False) \
            or (_tag_is(element, 'add') and first_layer is True) or _tag_is(element, 'note'):
        tokens = []
    elif _tag_is(element, 'abbr'):
        # Mark stars in the token 'n' form.
        if len(tokens) == 0:
            pass
        tokens[0]['n'] = '*%s*' % tokens[0]['t']

    # Finally handle the tail text of this element, if any.
    if element.tail is not None:
        # Strip any insignificant whitespace from the tail.
        tnode = element.tail
        if re.match('.*\}[clp]b$', element.tag):
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
    if token['lit'] != '':
        return False
    return True


if __name__ == '__main__':
    witness_array = []
    textms = None
    xmlfiles = None
    if re.match('.*\.xml$', sys.argv[1]) is None:
        textms = sys.argv[1]
        xmlfiles = sys.argv[2:]
    else:
        xmlfiles = sys.argv
    for fn in xmlfiles:
        sigil = re.sub('\.xml$', '', fn)
        with open(fn, encoding='utf-8') as xf:
            result = wordtokenize(xf, textms)
            if len(result):
                witness_array.append({'id': sigil, 'tokens': result})
    print(json.dumps({'witnesses': witness_array}, ensure_ascii=False))
