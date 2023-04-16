from typing import Union

from abc import abstractmethod

from src.base import SpeechTag, Span, Tag, QuantityType, OrderModifierData, CompounderData, SIPrefixData, SimpleUnitData


class NumberTag(SpeechTag):

    def __init__(self, span: Span, value: Union[float, int]):
        super().__init__(Tag.NUMBER, span, value)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<NUM {self.value} in {self.span}>'


class Quantity(SpeechTag):

    def __init__(self, span: Span, value: str, q_type: QuantityType):
        super().__init__(Tag.QUANTITY, span, value)
        self.q_type = q_type

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<QUAN {self.value} for {self.q_type.value[0]} in {self.span}>'


class UnitDespriptor(SpeechTag):

    def __init__(self, tag: Tag, span: Span):
        super().__init__(tag, span, None)

    @abstractmethod
    def to_si_coefficient(self) -> float:
        pass

    @abstractmethod
    def to_structure_tree(self):
        pass

    @abstractmethod
    def get_dimensions(self):
        pass


class SimpleUnit(UnitDespriptor):

    def __init__(self, span: Span, unit_text: str, unit_data: SimpleUnitData):
        super().__init__(Tag.SIMPLE_UNIT, span)
        self.unit_text = unit_text
        self.unit_data = unit_data

    def to_si_coefficient(self) -> float:
        return self.unit_data.to_si_coefficient()

    def to_structure_tree(self):
        return self.unit_text

    def get_dimensions(self):
        return self.unit_data.get_dimensions()

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<SUnit {self.unit_text} at {self.span}>'


class SIPrefix(UnitDespriptor):

    def __init__(self, span: Span, prefix_text: str, si_prefix_data: SIPrefixData):
        super().__init__(Tag.SI_PRIFIX, span)
        self.prefix_text = prefix_text
        self.si_prefix_data = si_prefix_data

    def to_si_coefficient(self) -> float:
        return self.si_prefix_data.to_si_coefficient()

    def to_structure_tree(self):
        return self.prefix_text,

    def get_dimensions(self):
        return QuantityType.get_zero_dimentions()

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<Pfx {self.prefix_text} at {self.span}>'


class OrderModifier(UnitDespriptor):

    def __init__(self, span: Span, modifier_text: str, order_modifier_data: OrderModifierData):
        super().__init__(Tag.ORDER_MODIFIER, span)
        self.modifier_text = modifier_text
        self.order_modifier_data = order_modifier_data

    def to_si_coefficient(self) -> float:
        # Never reach there
        raise NotImplemented

    def to_structure_tree(self):
        return self.modifier_text,

    def get_dimensions(self):
        # Never reach there
        raise NotImplemented

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<OMfr {self.modifier_text} at {self.span}'


class Compounder(UnitDespriptor):

    def __init__(self, span: Span, compounder_text: str, compounder_data: CompounderData):
        super().__init__(Tag.UNIT_COMPOUNDER_PREPOSITION, span)
        self.compounder_text = compounder_text
        self.compounder_data = compounder_data

    def to_si_coefficient(self) -> float:
        # Never reach there
        raise NotImplemented

    def to_structure_tree(self):
        return self.compounder_text,

    def get_dimensions(self):
        # Never reach there
        raise NotImplemented

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<Cmp {self.compounder_text} at {self.span}>'


class PrefixedUnit(UnitDespriptor):

    def __init__(self, si_prefix: SIPrefix, simple_unit: SimpleUnit):
        super().__init__(Tag.PREFIXED_UNIT, Span.combine(si_prefix.span if si_prefix else None, simple_unit.span))
        self.si_prefix = si_prefix
        self.simple_unit = simple_unit

    def to_si_coefficient(self) -> float:
        return (self.si_prefix.to_si_coefficient() if self.si_prefix else 1) * self.simple_unit.to_si_coefficient()

    def to_structure_tree(self):
        return {
            'پیشوند': self.si_prefix.to_structure_tree() if self.si_prefix else {},
            'یکا': self.simple_unit.to_structure_tree(),
        }

    def get_dimensions(self):
        return self.simple_unit.get_dimensions()

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<PfxUnit {self.si_prefix.__str__()} {self.simple_unit.__str__()} at {self.span}>'


class OrderedUnit(UnitDespriptor):

    def __init__(self, prefixed_unit: PrefixedUnit, order_modifier: OrderModifier):
        super().__init__(Tag.ORDERED_UNIT,
                         Span.combine(order_modifier.span if order_modifier else None, prefixed_unit.span))
        self.prefixed_unit = prefixed_unit
        self.order_modifier = order_modifier

    def to_si_coefficient(self) -> float:
        if self.order_modifier:
            return self.order_modifier.order_modifier_data.get_modified_coefficient(
                self.prefixed_unit.to_si_coefficient())
        else:
            return self.prefixed_unit.to_si_coefficient()

    def to_structure_tree(self):
        return {
            'واحد': self.prefixed_unit.to_structure_tree(),
            'تغییردهنده مرتبه': self.order_modifier.to_structure_tree() if self.order_modifier else {},
        }

    def get_dimensions(self):
        if self.order_modifier:
            get_modified = self.order_modifier.order_modifier_data.get_modified_dimention
            base_dimention, primaries = self.prefixed_unit.get_dimensions()
            return list(map(get_modified, base_dimention)), primaries
        else:
            return self.prefixed_unit.get_dimensions()

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<OrdUnit {self.order_modifier} {self.prefixed_unit} at {self.span}>'


class Unit(UnitDespriptor):

    def __init__(self, ordered_unit_1: OrderedUnit, ordered_unit_2: OrderedUnit, coumpounder: Compounder):
        super().__init__(Tag.UNIT, Span.combine(ordered_unit_1.span,
                                                ordered_unit_2.span if ordered_unit_2 else None,
                                                coumpounder.span if coumpounder else None))
        self.ordered_unit_1 = ordered_unit_1
        self.ordered_unit_2 = ordered_unit_2
        self.coumpounder = coumpounder

    def to_si_coefficient(self) -> float:
        if self.coumpounder:
            return self.coumpounder.compounder_data.get_modified_coefficient(
                self.ordered_unit_1.to_si_coefficient(),
                self.ordered_unit_2.to_si_coefficient()
            )
        return self.ordered_unit_1.to_si_coefficient()

    def to_structure_tree(self):
        return {
            'واحد اول': self.ordered_unit_1.to_structure_tree(),
            'واحد دوم': self.ordered_unit_2.to_structure_tree() if self.ordered_unit_2 else {},
            'مرکب ساز': self.coumpounder.to_structure_tree() if self.coumpounder else {},
        }

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'<Unit {self.ordered_unit_1} {self.coumpounder} {self.ordered_unit_2}>'

    def get_dimensions(self):
        if self.coumpounder:
            dim1, primaries = self.ordered_unit_1.get_dimensions()
            dim2, primaries = self.ordered_unit_2.get_dimensions()
            modifier = self.coumpounder.compounder_data.get_modified_dimention
            dim = list(map(lambda d_tuple: modifier(d_tuple[0], d_tuple[1]), zip(dim1, dim2)))
            return dim, primaries
        return self.ordered_unit_1.get_dimensions()

    def get_quantity_potential_names(self):
        return QuantityType.get_all_match_dimentsions(self.get_dimensions()[0])
