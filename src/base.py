import math

from enum import Enum

from typing import List
from typing import Tuple
from typing import Union
from typing import Callable


class QuantityType(Enum):
    LENGTH = [
        'طول',
        'فاصله',
        'مسافت',
        'اندازه',
    ]
    MASS = [
        'جرم',
        'وزن',
        'سنگینی',
        'سبکی',
    ]
    TEMPRETURE = [
        'دما',
        'سردی',
        'گرمی',
        'حرارت',
    ]
    TIME = [
        'زمان',
        'مدت',
        'بازه زمانی',
    ]
    DIGITAL_STORAGE = [
        'داده',
    ]
    SPEED = [
        'سرعت',
        'تندی',
    ]
    POWER = [
        'توان',
        'قدرت',
        'مصرف انرژی',
    ]
    TORQUE = [
        'گشتاور',
    ]
    DENSITY = [
        'چگالی',
        'جرم حجمی',
    ]
    FREQUENCY = [
        'فرکانس',
        'بسامد',
    ]
    ANGLE = [
        'زاویه',
        'کنج',
    ]
    ACCELERATION = [
        'شتاب'
    ]
    AREA = [
        'مساحت',
        'سطح',
        'پهنا',
    ]
    VOULME = [
        'حجم',
        'گنجایش',
    ]
    FORCE = [
        'نیرو'
    ]
    ENERGY = [
        'انرژی',
        'قوه',
    ]
    PRESSURE = [
        'فشار'
    ]
    MASS_FLOW = [
        'شارش جرم',
        'شارش وزن',
        'جویبار جرم',
        'جویبار وزن',
        'شارش جرمی',
        'شارش وزنی',
        'جویبار جرمی',
        'جویبار وزنی',
    ]
    VOLUMETRIC_FLOW = [
        'شارش حجم',
        'شارش حجمی',
        'آبدهی',
        'آب‌دهی',
        'آب دهی',
        'دبی',
    ]
    DATA_TRANSFER_RATE = [
        'نرخ انتقال',
        'نرخ'
    ]

    @staticmethod
    def get_primaries():
        return [
            QuantityType.LENGTH,
            QuantityType.MASS,
            QuantityType.TEMPRETURE,
            QuantityType.TIME,
            QuantityType.DIGITAL_STORAGE
        ]

    def get_dimentions(self):
        primaries = self.get_primaries()
        if self in primaries:
            dimentions = [0, ] * 5
            dimentions[primaries.index(self)] = 1
        elif self == QuantityType.SPEED:
            dimentions = [1, 0, 0, -1, 0]
        elif self == QuantityType.POWER:
            dimentions = [2, 1, 0, -3, 0]
        elif self == QuantityType.TORQUE:
            dimentions = [2, 1, 0, -2, 0]
        elif self == QuantityType.DENSITY:
            dimentions = [-3, 1, 0, 0, 0]
        elif self == QuantityType.FREQUENCY:
            dimentions = [0, 0, 0, -1, 0]
        elif self == QuantityType.ANGLE:
            dimentions = [0, 0, 0, 0, 0]
        elif self == QuantityType.ACCELERATION:
            dimentions = [1, 0, 0, -2, 0]
        elif self == QuantityType.AREA:
            dimentions = [2, 0, 0, 0, 0]
        elif self == QuantityType.VOULME:
            dimentions = [3, 0, 0, 0, 0]
        elif self == QuantityType.FORCE:
            dimentions = [1, 1, 0, -2, 0]
        elif self == QuantityType.ENERGY:
            dimentions = [2, 1, 0, -2, 0]
        elif self == QuantityType.PRESSURE:
            dimentions = [-2, 1, 0, 0, 0]
        elif self == QuantityType.MASS_FLOW:
            dimentions = [0, 1, 0, -1, 0]
        elif self == QuantityType.VOLUMETRIC_FLOW:
            dimentions = [3, 0, 0, -1, 0]
        elif self == QuantityType.DATA_TRANSFER_RATE:
            dimentions = [0, 0, 0, -1, 1]
        return dimentions, primaries

    @staticmethod
    def get_all_match_dimentsions(dims: List[int]) -> List:
        matches = []
        for quantity in QuantityType:
            if quantity.get_dimentions()[0] == dims:
                matches.append(quantity)
        return matches

    @staticmethod
    def get_zero_dimentions():
        primaries = QuantityType.get_primaries()
        return [0, ] * len(primaries), primaries


class Tag(Enum):
    ADJECTIVE = 'J'
    NOUN = 'N'
    NUMBER = 'D'
    QUANTITY = 'Q'
    UNIT = 'U'

    ORDERED_UNIT = 'O'
    PREFIXED_UNIT = 'P'

    SIMPLE_UNIT = 'u'
    SI_PRIFIX = 'p'
    ORDER_MODIFIER = 'm'
    UNIT_COMPOUNDER_PREPOSITION = 'c'


class Span(object):

    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def to_tuple(self) -> Tuple[int, int]:
        return self.start, self.end

    def combine(*spans):
        spans = list(filter(lambda st: not (st is None), spans))
        return Span(min(map(lambda st: st.start, spans)),
                    max(map(lambda st: st.end, spans)))

    def is_overlapped(self, other) -> bool:
        start_max = max(self.start, other.start)
        end_min = min(self.end, other.end)
        return start_max < end_min

    def get_str(self, org_str: str) -> str:
        return org_str[self.start: self.end]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return str(self.to_tuple())


class SpeechTag(object):

    def __init__(self, tag: Tag, span: Span, value: Union[int, float, str, None]):
        self.tag = tag
        self.span = span
        self.value = value

    @staticmethod
    def to_pattern_str(st_list):
        return ''.join(map(lambda st: st.tag.value, st_list))


class SpeechTagsPipeline(object):

    def __init__(self, pipes: List[Callable[[str, List[SpeechTag]], List[SpeechTag]]]):
        self.pipes = pipes

    def run(self, org_str: str) -> List[SpeechTag]:
        speech_tags = []
        for pipe in self.pipes:
            speech_tags = pipe(org_str, speech_tags)

        return speech_tags


def mask_string(speech_tags: List[SpeechTag], original_string: str):
    masked_string = original_string[:]
    for spch_tag in speech_tags:
        start_of_span = spch_tag.span.start
        end_of_span = spch_tag.span.end
        tag_length = end_of_span - start_of_span
        tag_enum_value = str(spch_tag.tag.value)
        masked_string = masked_string[:start_of_span] + (tag_enum_value * tag_length) + masked_string[end_of_span:]
    return masked_string


class SimpleUnitData(object):

    def __init__(self, unit_name: str, q_type: QuantityType, symbol: str, coefficient: float, si: bool,
                 matchable: bool):
        self.unit_name = unit_name
        self.q_type = q_type
        self.symbol = symbol
        self.coefficient = coefficient
        self.si = si
        self.matchable = matchable

    def to_si_coefficient(self) -> float:
        return self.coefficient

    def get_dimensions(self):
        return self.q_type.get_dimentions()


class SIPrefixData(object):

    def __init__(self, prefix_name: str, symbol: str, coefficient: float):
        self.prefix_name = prefix_name
        self.symbol = symbol
        self.coefficient = coefficient

    def to_si_coefficient(self) -> float:
        return self.coefficient


si_prefixes = [
    SIPrefixData('یوتا', 'Y', 1e24),
    SIPrefixData('زتا', 'Z', 1e21),
    SIPrefixData('اگزا', 'E', 1e18),
    SIPrefixData('اگزو', 'E', 1e18),
    SIPrefixData('پتا', 'P', 1e15),
    SIPrefixData('ترا', 'T', 1e12),
    SIPrefixData('گیگا', 'G', 1e9),
    SIPrefixData('مگا', 'M', 1e6),
    SIPrefixData('کیلو', 'K', 1e3),
    SIPrefixData('کیلو', 'k', 1e3),
    SIPrefixData('هکتو', 'h', 1e2),
    SIPrefixData('دکا', 'da', 1e1),
    SIPrefixData('دسی', 'd', 1e-1),
    SIPrefixData('سانتی', 'c', 1e-2),
    SIPrefixData('میلی', 'm', 1e-3),
    SIPrefixData('میکرو', 'µ', 1e-6),
    SIPrefixData('نانو', 'n', 1e-9),
    SIPrefixData('پیکو', 'p', 1e-12),
    SIPrefixData('فمتو', 'f', 1e-15),
    SIPrefixData('آتو', 'a', 1e-18),
    SIPrefixData('اتو', 'a', 1e-18),
    SIPrefixData('زپتو', 'z', 1e-21),
    SIPrefixData('یوکتو', 'y', 1e-24),
    SIPrefixData('یکتو', 'y', 1e-24),
]


class OrderModifierData(object):

    def __init__(self, modifier_name: str, get_modified_coefficient: Callable[[float], float],
                 get_modified_dimention: Callable[[float], float]):
        self.modifier_name = modifier_name
        self.get_modified_coefficient = get_modified_coefficient
        self.get_modified_dimention = get_modified_dimention


order_modifiers = [
    OrderModifierData('جذر', lambda c: math.sqrt(c), lambda d: d / 2),
    OrderModifierData('مجذور', lambda c: c ** 2, lambda d: 2 * d),
    OrderModifierData('مربع', lambda c: c ** 2, lambda d: 2 * d),
    OrderModifierData('مکعب', lambda c: c ** 3, lambda d: 3 * d),
]


class CompounderData(object):

    def __init__(self, cmp_name: str, divider: bool):
        self.cmp_name = cmp_name
        self.divider = divider

    def get_modified_coefficient(self, c1, c2):
        return c1 / c2 if self.divider else c1 + c2

    def get_modified_dimention(self, d1, d2):
        return d1 - d2 if self.divider else d1 + d2


compounders = [
    CompounderData('در', False),
    CompounderData('.', False),
    CompounderData('-', False),
    CompounderData('/', True),
    CompounderData('\\', True),
    CompounderData('بر', True),
]

zero_compounder = CompounderData('', False)


class Metric(object):

    def __init__(self, q_type: str, amount: str, unit: str, item: str, marker: str, span: tuple):
        self.q_type = q_type
        self.amount = amount
        self.unit = unit
        self.item = item
        self.marker = marker
        self.span = span

    def __str__(self):
        return str({
            'type': self.q_type,
            'amount': self.amount,
            'unit': self.unit,
            'item': self.item,
            'marker': self.marker,
            'span': self.span
        })
