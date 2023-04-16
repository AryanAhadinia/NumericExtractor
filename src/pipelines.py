import re

from typing import List

import pandas as pd

from resources.parsi_io.modules.number_extractor import NumberExtractor
import hazm

from src.base import SpeechTag, Span, QuantityType, SimpleUnitData, si_prefixes, order_modifiers, compounders, Tag, \
    zero_compounder
from src.speech_tags import NumberTag, Quantity, SimpleUnit, SIPrefix, OrderModifier, Compounder, PrefixedUnit, \
    OrderedUnit, Unit
from src.utils import logical_or, mask_string

default_number_extractor = NumberExtractor()


def convert_to_english_num(persian_num):
    per = ord('۰')
    eng = ord('0')
    for i in range(9):
        persian_num = persian_num.replace(chr(per + i), chr(eng + i))

    return persian_num


def number_extractor(org_str: str) -> List[SpeechTag]:
    speech_tags = []
    digit = '[۰-۹0-9]'
    float_reg = f'[\+-]?(({digit}+(\.{digit}+)?)|(\.{digit}+))'
    scientific_reg = float_reg + f'(([\*x]10((\^|(\*\*)){digit}+)?)|(e[\+-]?{digit}+))?'
    for match in re.finditer(scientific_reg, org_str):
        pythonic_num = match.group(0).replace('^', '**').replace('x', '*')
        pythonic_num = convert_to_english_num(pythonic_num)
        speech_tags.append(NumberTag(Span(*match.span()), eval(pythonic_num)))

    return speech_tags


def get_number_tags_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    scientific_nums = number_extractor(org_str)
    speech_tags = speech_tags + scientific_nums

    for num in default_number_extractor.run(org_str):
        num_span = Span(num['span'][0], num['span'][1])
        if not any([x.span.is_overlapped(num_span) for x in scientific_nums]):
            speech_tags.append(NumberTag(num_span, num['value']))
    return speech_tags


name_quantity = {}
for quantity in QuantityType:
    for name in quantity.value:
        name_quantity[name] = quantity

quantity_names_sorted = sorted(name_quantity.keys(), key=lambda q_name: len(q_name), reverse=True)


def get_quantity_name_tags_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    for quantity_name in quantity_names_sorted:
        start_index = 0
        while True:
            first_char_index = org_str.find(quantity_name, start_index)
            if first_char_index == -1:
                break
            start_index = first_char_index + 1
            span = Span(first_char_index, first_char_index + len(quantity_name))
            overlapped = logical_or(map(lambda st: span.is_overlapped(st.span), speech_tags))
            if not overlapped:
                quantity_tag = Quantity(span, span.get_str(org_str), name_quantity[quantity_name])
                speech_tags.append(quantity_tag)
    return speech_tags


units_df = pd.read_csv('resources/units.csv')

simple_units = []
for idx, row in units_df.iterrows():
    sud = SimpleUnitData(row['unit'],
                         name_quantity[row['quantity']],
                         row['symbol'], row['coefficient'],
                         row['SI'],
                         row['Match'])
    simple_units.append(sud)

unit_quantity = {s.unit_name: s for s in filter(lambda s: s.matchable, simple_units)}
unit_names_sorted = sorted(unit_quantity.keys(), key=lambda s: len(s), reverse=True)

unit_quantity_by_symbol = {s.symbol: s for s in filter(lambda s: s.matchable, simple_units)}
unit_names_sorted_by_symbol = sorted(list(filter(lambda x: not pd.isna(x), unit_quantity_by_symbol.keys())),
                                     key=lambda s: len(s), reverse=True)

gram_data = SimpleUnitData('گرم', QuantityType.MASS, 'g', 1, True, True)


def get_simple_unit_tags_on_names_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    for unit_name in unit_names_sorted:
        start_index = 0
        while True:
            first_char_index = org_str.find(unit_name, start_index)
            if first_char_index == -1:
                break
            start_index = first_char_index + 1
            span = Span(first_char_index, first_char_index + len(unit_name))
            overlapped = logical_or(map(lambda st: span.is_overlapped(st.span), speech_tags))
            if not overlapped:
                found_str = span.get_str(org_str)
                simple_unit_tag = SimpleUnit(span, found_str, unit_quantity[found_str])
                speech_tags.append(simple_unit_tag)
    return speech_tags


def get_simple_unit_tags_on_symbols_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    for unit_name in unit_names_sorted_by_symbol:
        start_index = 0
        while True:
            first_char_index = org_str.find(unit_name, start_index)
            if first_char_index == -1:
                break
            start_index = first_char_index + 1
            span = Span(first_char_index, first_char_index + len(unit_name))
            overlapped = logical_or(map(lambda st: span.is_overlapped(st.span), speech_tags))
            if not overlapped:
                found_str = span.get_str(org_str)
                simple_unit_tag = SimpleUnit(span, found_str, unit_quantity_by_symbol[found_str])
                speech_tags.append(simple_unit_tag)
    return speech_tags


def get_si_prefix_tags_on_names_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    for prefix in sorted(si_prefixes, key=lambda sip: len(sip.prefix_name), reverse=True):
        start_index = 0
        prefix_str = prefix.prefix_name
        while True:
            first_char_index = org_str.find(prefix_str, start_index)
            if first_char_index == -1:
                break
            start_index = first_char_index + 1
            span = Span(first_char_index, first_char_index + len(prefix_str))
            overlapped = logical_or(map(lambda st: span.is_overlapped(st.span), speech_tags))
            if not overlapped:
                prefix_tag = SIPrefix(span, span.get_str(org_str), prefix)
                speech_tags.append(prefix_tag)
    return speech_tags


def get_si_prefix_tags_on_symbols_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    for prefix in sorted(si_prefixes, key=lambda sip: len(sip.symbol), reverse=True):
        start_index = 0
        prefix_str = prefix.symbol
        while True:
            first_char_index = org_str.find(prefix_str, start_index)
            if first_char_index == -1:
                break
            start_index = first_char_index + 1
            span = Span(first_char_index, first_char_index + len(prefix_str))
            overlapped = logical_or(map(lambda st: span.is_overlapped(st.span), speech_tags))
            if not overlapped:
                prefix_tag = SIPrefix(span, span.get_str(org_str), prefix)
                speech_tags.append(prefix_tag)
    return speech_tags


def get_order_modifier_tags_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    for modifier in order_modifiers:
        start_index = 0
        modifier_str = modifier.modifier_name
        while True:
            first_char_index = org_str.find(modifier_str, start_index)
            if first_char_index == -1:
                break
            start_index = first_char_index + 1
            span = Span(first_char_index, first_char_index + len(modifier_str))
            overlapped = logical_or(map(lambda st: span.is_overlapped(st.span), speech_tags))
            if not overlapped:
                modifier_tag = OrderModifier(span, span.get_str(org_str), modifier)
                speech_tags.append(modifier_tag)
    return speech_tags


def get_unit_compounder_preposition_tags_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    for compounder in compounders:
        start_index = 0
        compounder_str = compounder.cmp_name
        while True:
            first_char_index = org_str.find(compounder_str, start_index)
            if first_char_index == -1:
                break
            start_index = first_char_index + 1
            span = Span(first_char_index, first_char_index + len(compounder_str))
            overlapped = logical_or(map(lambda st: span.is_overlapped(st.span), speech_tags))
            if not overlapped:
                compounder_tag = Compounder(span, span.get_str(org_str), compounder)
                speech_tags.append(compounder_tag)
    return speech_tags


def speech_tags_sorter_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    return sorted(speech_tags, key=lambda st: st.span.start)


def gram_generator(span_start: int):
    return SimpleUnit(Span(span_start, span_start), '', gram_data)


def get_prefixed_units_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    if len(speech_tags) == 0:
        return []
    st = speech_tags[0]
    if len(speech_tags) == 1:
        if st.tag == Tag.SIMPLE_UNIT:
            return [PrefixedUnit(None, st), ]
        if st.tag == Tag.SI_PRIFIX and st.si_prefix_data.prefix_name == 'کیلو':
            return [PrefixedUnit(st, gram_generator(st.span.end)), ]
        return [st]
    st_next = speech_tags[1]
    if st.tag == Tag.SI_PRIFIX and st_next.tag == Tag.SIMPLE_UNIT:
        return [PrefixedUnit(st, st_next), ] + get_prefixed_units_pipe(org_str, speech_tags[2:])
    if st.tag == Tag.SIMPLE_UNIT:
        return [PrefixedUnit(None, st), ] + get_prefixed_units_pipe(org_str, speech_tags[1:])
    if st.tag == Tag.SI_PRIFIX and st.si_prefix_data.prefix_name == 'کیلو':
        return [PrefixedUnit(st, gram_generator(st.span.end)), ] + get_prefixed_units_pipe(org_str,
                                                                                           speech_tags[1:])  # TODO
    return [st, ] + get_prefixed_units_pipe(org_str, speech_tags[1:])


def get_ordered_units_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    if len(speech_tags) == 0:
        return []
    st = speech_tags[0]
    if len(speech_tags) == 1:
        if st.tag == Tag.PREFIXED_UNIT:
            return [OrderedUnit(st, None), ]
        return [st, ]
    st_next = speech_tags[1]
    if st.tag == Tag.ORDER_MODIFIER and st_next.tag == Tag.PREFIXED_UNIT:
        return [OrderedUnit(st_next, st), ] + get_ordered_units_pipe(org_str, speech_tags[2:])
    if st.tag == Tag.PREFIXED_UNIT and st_next.tag == Tag.ORDER_MODIFIER and st.get_dimensions() == QuantityType.LENGTH.get_dimentions() and (
            st_next.order_modifier_data.modifier_name == 'مربع' or st_next.order_modifier_data.modifier_name == 'مکعب'):
        return [OrderedUnit(st, st_next), ] + get_ordered_units_pipe(org_str, speech_tags[2:])
    if st.tag == Tag.PREFIXED_UNIT:
        return [OrderedUnit(st, None), ] + get_ordered_units_pipe(org_str, speech_tags[1:])
    return [st, ] + get_ordered_units_pipe(org_str, speech_tags[1:])


def get_units_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    if len(speech_tags) == 0:
        return []
    st = speech_tags[0]
    if len(speech_tags) == 1:
        if st.tag == Tag.ORDERED_UNIT:
            return [Unit(st, None, None), ]
        return [st, ]
    st_1 = speech_tags[1]
    if len(speech_tags) == 2:
        if st.tag == Tag.UNIT and st_1.tag == Tag.ORDERED_UNIT:
            zero_cmp_span = Span(st.span.end, st_1.span.start)
            zero_cmp = Compounder(zero_cmp_span, zero_cmp_span.get_str(org_str), zero_compounder)
            return [Unit(st, st_1, zero_cmp), ]
        if st.tag == Tag.ORDERED_UNIT:
            return get_units_pipe(org_str, [Unit(st, None, None), ] + speech_tags[1:])
        return [st, ] + get_units_pipe(org_str, speech_tags[1:])
    st_2 = speech_tags[2]
    if st.tag == Tag.UNIT and st_1.tag == Tag.UNIT_COMPOUNDER_PREPOSITION and st_2.tag == Tag.ORDERED_UNIT:
        return get_units_pipe(org_str, [Unit(st, st_2, st_1), ] + speech_tags[3:])
    if st.tag == Tag.UNIT and st_1.tag == Tag.ORDERED_UNIT:
        zero_cmp_span = Span(st.span.end, st_1.span.start)
        zero_cmp = Compounder(zero_cmp_span, zero_cmp_span.get_str(org_str), zero_compounder)
        return get_units_pipe(org_str, [Unit(st, st_1, zero_cmp), ] + speech_tags[2:])
    if st.tag == Tag.ORDERED_UNIT:
        return get_units_pipe(org_str, [Unit(st, None, None), ] + speech_tags[1:])
    return [st, ] + get_units_pipe(org_str, speech_tags[1:])


def filter_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    new_st = []
    for st in speech_tags:
        if st.tag == Tag.UNIT or st.tag == Tag.NUMBER or st.tag == Tag.QUANTITY:
            new_st.append(st)
    return new_st


# all tags (kinda):
# 'ADV','ADVe','AJ','AJe','CL','CONJ','DET','DETe','N','NUM','NUMe','Ne','P','POSTP','PRO','PUNC','Pe','V'
# im gonna take AJ as adjective and N, Ne and PRO as noun
tagger = hazm.POSTagger(model='resources/postagger.model')


def get_postags_pipe(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    masked = mask_string(speech_tags, org_str)
    tagged_tokens = tagger.tag(masked.split())

    last_span = None
    for i in range(len(tagged_tokens)):
        strt = 0 if not i else last_span[1] + 1
        end = strt + len(tagged_tokens[i][0])
        last_span = (strt, end)

        word, tag = tagged_tokens[i]
        if tag == 'AJ':
            aj_tag = SpeechTag(Tag.ADJECTIVE, Span(strt, end), word)
            if not any([aj_tag.span.is_overlapped(x.span) for x in speech_tags]):
                speech_tags.append(aj_tag)
        elif tag in ['N', 'Ne', 'PRO']:
            noun_tag = SpeechTag(Tag.NOUN, Span(strt, end), word)
            if not any([noun_tag.span.is_overlapped(x.span) for x in speech_tags]):
                speech_tags.append(noun_tag)

    return speech_tags
