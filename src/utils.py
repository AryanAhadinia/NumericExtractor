import re

from typing import Iterable
from typing import List

from typing import Union

from resources.parsi_io.modules.number_extractor import NumberExtractor

from src.base import SpeechTag, Span, Metric, Tag
from src.speech_tags import Unit, Quantity, NumberTag


def logical_or(bool_list: Iterable[bool]) -> bool:
    for boolean in bool_list:
        if boolean:
            return True
    return False


def logical_and(bool_list: Iterable[bool]) -> bool:
    for boolean in bool_list:
        if not boolean:
            return False
    return True


def mask_string(speech_tags: List[SpeechTag], original_string: str):
    masked_string = original_string[:]
    for spch_tag in speech_tags:
        start_of_span = spch_tag.span.start
        end_of_span = spch_tag.span.end
        tag_length = end_of_span - start_of_span
        tag_enum_value = str(spch_tag.tag.value)
        masked_string = masked_string[:start_of_span] + (tag_enum_value * tag_length) + masked_string[end_of_span:]
    return masked_string


def delete_unwanted_parts(speech_tags: List[SpeechTag], original_string: str):
    masked_string = original_string[:]
    for spch_tag in speech_tags:
        start_of_span = spch_tag.span.start
        end_of_span = spch_tag.span.end
        tag_length = end_of_span - start_of_span
        masked_string = masked_string[:start_of_span] + (' ' * tag_length) + masked_string[end_of_span:]
    return masked_string


def find_tag(tag_span, speech_tags):
    start_span = tag_span[0]
    end_span = tag_span[1]
    returned_tag = None
    for spch_tag in speech_tags:
        if spch_tag.span.start == start_span and spch_tag.span.end == end_span:
            returned_tag = spch_tag
            break
    return returned_tag


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


def find_number(original_string, number_span):
    start_span = number_span[0]
    end_span = number_span[1]
    number_string = original_string[start_span:end_span]
    return get_number_tags_pipe(number_string, [])[0].value


def find_tags(found_span, speech_tags):
    found_tags = []
    for spch_tag in speech_tags:
        if spch_tag.span.is_overlapped(found_span):
            found_tags.append(spch_tag)
    return found_tags


def find_unit_span(part_masked_string, span_start):
    pattern = re.compile('U+')
    matches = pattern.search(part_masked_string)
    returned_span = (span_start + matches.span()[0], span_start + matches.span()[1])
    return returned_span


def find_number_span(part_masked_string, span_start):
    pattern = re.compile('D+')
    matches = pattern.search(part_masked_string)
    returned_span = (span_start + matches.span()[0], span_start + matches.span()[1])
    return returned_span


def find_quantity_span(part_masked_string, span_start):
    pattern = re.compile('Q+')
    matches = pattern.search(part_masked_string)
    returned_span = (span_start + matches.span()[0], span_start + matches.span()[1])
    return returned_span


def find_noun_span(part_masked_string, span_start):
    pattern = re.compile('N+')
    matches = pattern.search(part_masked_string)
    returned_span = (span_start + matches.span()[0], span_start + matches.span()[1])
    return returned_span


def find_numbers_span_special(part_masked_string, span_start):
    pattern = re.compile('D+')
    matches = pattern.finditer(part_masked_string)
    spans_list = []
    for match in matches:
        spans_list.append((span_start + match.span()[0], span_start + match.span()[1]))
    return spans_list


def create_object_for_group(have_digit, have_noun, have_unit, have_quantity, part_masked_string, speech_tags,
                            original_string, span_start):
    object_type = ""
    object_amount = ""
    object_unit = ""
    object_item = ""
    if have_unit:
        unit_span = find_unit_span(part_masked_string, span_start)
        object_unit = original_string[unit_span[0]:unit_span[1]]
        unit_tag = find_tag(unit_span, speech_tags)
        object_type = unit_tag.get_quantity_potential_names()[0]
    if have_digit:
        number_span = find_number_span(part_masked_string, span_start)
        object_amount = find_number(original_string, number_span)
    if have_noun:
        noun_span = find_noun_span(part_masked_string, span_start)
        object_item = original_string[noun_span[0]:noun_span[1]]
    if have_quantity and not have_unit:
        quantity_span = find_quantity_span(part_masked_string, span_start)
        quantity_tag = find_tag(quantity_span, speech_tags)
        object_type = quantity_tag.q_type[0]

    return object_type, object_amount, object_unit, object_item


def create_object(match, match_group, original_string, masked_string, speech_tags):
    span_start = match.span()[0]
    span_end = match.span()[1]
    match_span = Span(span_start, span_end)
    part_masked_string = masked_string[span_start:span_end]

    desired_speech_tags = find_tags(match_span, speech_tags)

    object_marker = original_string[span_start:span_end]
    object_span = match.span()

    if match_group == 1:
        # unit_span = find_unit_span(part_masked_string)
        # object_unit = original_string[unit_span[0]:unit_span[1]]
        # unit_tag = find_tag(unit_span, speech_tags)
        # object_type = unit_tag.get_quantity_name()
        # number_span = find_number_span(part_masked_string)
        # object_amount = find_number(original_string, number_span)
        # noun_span = find_noun_span(part_masked_string)
        # object_item = original_string[noun_span[0]:noun_span[1]]
        # return Metric(object_type, object_amount, object_unit, object_item, object_marker, object_span)
        wanted_parts = create_object_for_group(True, True, True, False, part_masked_string, speech_tags,
                                               original_string, span_start)
        # metric_generated = Metric(wanted_parts[0], wanted_parts[1], wanted_parts[2], wanted_parts[3], object_marker, object_span)
    elif match_group == 2:
        wanted_parts = create_object_for_group(True, False, True, False, part_masked_string, speech_tags,
                                               original_string, span_start)
    elif match_group == 3:
        wanted_parts = create_object_for_group(True, True, True, True, part_masked_string, speech_tags, original_string,
                                               span_start)
    elif match_group == 4:
        wanted_parts = create_object_for_group(True, True, True, True, part_masked_string, speech_tags, original_string,
                                               span_start)
    elif match_group == 5:
        wanted_parts = create_object_for_group(True, True, True, False, part_masked_string, speech_tags,
                                               original_string, span_start)
    elif match_group == 6:
        wanted_parts = create_object_for_group(True, True, True, False, part_masked_string, speech_tags,
                                               original_string, span_start)
    elif match_group == 7:
        wanted_parts = create_object_for_group(False, False, False, True, part_masked_string, speech_tags,
                                               original_string, span_start)
    elif match_group == 8:
        wanted_parts = create_object_for_group(True, True, True, True, part_masked_string, speech_tags, original_string,
                                               span_start)
    elif match_group == 9:
        wanted_parts = create_object_for_group(True, False, True, True, part_masked_string, speech_tags,
                                               original_string, span_start)
    elif match_group == 10:
        unit_span = find_unit_span(part_masked_string, span_start)
        object_unit = original_string[unit_span[0]:unit_span[1]]
        unit_tag = find_tag(unit_span, speech_tags)
        object_type = unit_tag.get_quantity_name()
        numbers_span = find_numbers_span_special(part_masked_string, span_start)
        first_number = find_number(original_string, numbers_span[0])
        second_number = find_number(original_string, numbers_span[1])
        object_amount = f'{first_number},{second_number}'
        wanted_parts = (object_type, object_amount, object_unit, "")
    else:
        unit_span = find_unit_span(part_masked_string, span_start)
        object_unit = original_string[unit_span[0]:unit_span[1]]
        unit_tag = find_tag(unit_span, speech_tags)
        object_type = unit_tag.get_quantity_name()
        numbers_span = find_numbers_span_special(part_masked_string, span_start)
        first_number = find_number(original_string, numbers_span[0])
        second_number = find_number(original_string, numbers_span[1])
        object_amount = f'{first_number},{second_number}'
        noun_span = find_noun_span(part_masked_string, span_start)
        object_item = original_string[noun_span[0]:noun_span[1]]
        wanted_parts = (object_type, object_amount, object_unit, object_item)

    metric_generated = Metric(wanted_parts[0], wanted_parts[1], wanted_parts[2], wanted_parts[3], object_marker,
                              object_span)
    return metric_generated


def new_create_object(match, match_group, original_string, masked_string, speech_tags):
    span_start = match.span()[0]
    span_end = match.span()[1]
    match_span = Span(span_start, span_end)
    part_masked_string = masked_string[span_start:span_end]

    desired_speech_tags = find_tags(match_span, speech_tags)

    object_type = ""
    object_amount = ""
    object_unit = ""
    object_item = ""
    object_marker = original_string[span_start:span_end]
    object_span = match.span()

    have_unit = False

    for spch_tag in desired_speech_tags:
        if isinstance(spch_tag, Unit):  # found a unit
            have_unit = True
            object_unit = original_string[spch_tag.span.start: spch_tag.span.end]
            # object_unit = spch_tag.value
            # for key in spch_tag.get_quantity_potential_names()[0]:
            # print(spch_tag.get_quantity_potential_names())
            if spch_tag.get_quantity_potential_names():
                object_type = spch_tag.get_quantity_potential_names()[0].value[0]
        elif isinstance(spch_tag, NumberTag):
            object_amount = spch_tag.value
            # object_amount = find_number(original_string, (spch_tag.span.start, spch_tag.span.end))
        elif spch_tag.tag == Tag.NOUN:
            object_item = str(spch_tag.value)
        elif isinstance(spch_tag, Quantity) and not have_unit:
            object_type = spch_tag.q_type.value[0]

    return Metric(object_type, object_amount, object_unit, object_item, object_marker, object_span)


def convert(val: Union[int, float], origin: Unit, target: Unit) -> Union[int, float]:
    conversion_factor = origin.to_si_coefficient() / target.to_si_coefficient()
    return conversion_factor * val


def filter_non_units(org_str: str, speech_tags: List[SpeechTag]) -> List[SpeechTag]:
    new_st = []
    for st in speech_tags:
        if st.tag == Tag.UNIT:
            new_st.append(st)
    return new_st


patterns = [
    'D+\s*U+\s*N+',  # علی ۳۰۰ کیلو شیشه خرید (also handles 200kg) 1
    'D+\s*U+',  # اتوبان ۲۰۰ دقیقه تا فلان فاصله دارد  2
    'Q+\s*N+\s*J+\s*D+\s*U+',  # وزن علی کوچولو ۲۰۰ کیلو است 3
    'Q+\s*N+\s*D+\s*U+',  # وزن علی ۲۰۰ کیلو است 4
    'N+\s*J+\s*D+\s*U+',  # علی کوچولو ۲۰۰ کیلو است 5
    'Q+\s*J+',  # سرعت زیاد 7
    'N+\s*D+\s*U+\s*Q+',  # شیشه ۲۰۰ کیلو وزن دارد 8
    'Q+\s*D+\s*U+',  # به وزن ۲۰۰ کیلو 9
    'D+\s*U+\s*.\s*D+\s*U+',
    'D+\s*U+\s*.\s*D+\s*U+\s*N+',  # ۲ متر و ۳۰ سانت پارچه خرید 11
]


def match_patterns(original_string: str, speech_tags: List[SpeechTag]):
    # print(f"org: {original_string}, tags = {speech_tags}")
    # for spch_tag in speech_tags:
    # print(f"tag: {spch_tag.value}")
    masked_string = mask_string(speech_tags, original_string)
    # print(masked_string)
    the_pattern = re.compile("(" + ")|(".join(patterns) + ")")
    # match_result = re.search(the_pattern, masked_string)
    matches = the_pattern.finditer(masked_string)
    final_objects = []
    for match in matches:
        match_group = [i for i, v in enumerate(match.groups()) if v != None][0]
        # print(match.span())
        # print(match_group)
        # print("yehllo")
        final_objects.append(new_create_object(match, match_group, original_string, masked_string, speech_tags))

    return final_objects
