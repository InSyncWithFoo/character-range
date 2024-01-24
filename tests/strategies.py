from collections.abc import Callable, Iterable
from typing import Any, ParamSpec, TypeVar

from _pytest.mark import ParameterSet
from hypothesis import example
from hypothesis.strategies import from_type, integers, just, one_of, sampled_from, SearchStrategy, tuples

from character_range import ByteInterval, CharacterInterval
from character_range.intervals import Interval


_T = TypeVar('_T')
_P = ParamSpec('_P')
_Decorator = Callable[[Callable[_P, _T]], Callable[_P, _T]]

_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def _int_to_byte(value: int, /) -> bytes:
	return value.to_bytes(1, 'big')


def _is_not_character(example: object, /) -> bool:
	return not isinstance(example, str) or len(example) != 1


def _is_not_byte(example: object, /) -> bool:
	return not isinstance(example, bytes) or len(example) != 1


def to_range(endpoints: tuple[int, int], /) -> range:
	start, end = sorted(endpoints)
	return range(start, end + 1)


def tupled_with_invalid_index(
	interval: Interval
) -> SearchStrategy[tuple[Interval, int]]:
	return tuples(
		just(interval),
		one_of([
			integers(min_value = len(interval)),
			integers(max_value = ~len(interval))
		])
	)


def tupled_with_class(cls: type[_T1]) -> Callable[[_T2], tuple[_T2, type[_T1]]]:
	def inner(example: _T2) -> tuple[_T2, type[_T1]]:
		return example, cls
	
	return inner


# Originally from https://stackoverflow.com/a/70312417
def examples(
	parameter_sets: Iterable[ParameterSet | tuple[Any, ...] | Any]
) -> _Decorator[_P, _T]:
	parameter_sets = list(parameter_sets)
	
	def inner(test_case: Callable[_P, _T]) -> Callable[_P, _T]:
		for parameter_set in reversed(parameter_sets):
			if isinstance(parameter_set, ParameterSet):
				parameter_set = parameter_set.values
			
			if not isinstance(parameter_set, tuple):
				parameter_set = tuple([parameter_set])
			
			test_case = example(*parameter_set)(test_case)
		
		return test_case
	
	return inner


def range_and_random_item(
	codepoint_range: range, /
) -> SearchStrategy[tuple[range, int]]:
	return tuples(just(codepoint_range), sampled_from(codepoint_range))


def range_and_random_index(
	codepoint_range: range, /
) -> SearchStrategy[tuple[range, int]]:
	indices = integers(min_value = 0, max_value = len(codepoint_range) - 1)
	
	return tuples(just(codepoint_range), indices)


def codepoints() -> SearchStrategy[int]:
	return integers(min_value = 0, max_value = 0x10FFFF)


def byte_codepoints() -> SearchStrategy[int]:
	return integers(min_value = 0, max_value = 0xFF)


def character_endpoints() -> SearchStrategy[str]:
	return codepoints().map(chr)


def byte_endpoints() -> SearchStrategy[bytes]:
	return byte_codepoints().map(_int_to_byte)


def non_character_endpoints() -> SearchStrategy[object]:
	return from_type(object).filter(_is_not_character)


def non_byte_endpoints() -> SearchStrategy[object]:
	return from_type(object).filter(_is_not_byte)


def non_strings() -> SearchStrategy[object]:
	return from_type(object).filter(lambda x: not isinstance(x, str))


def non_bytes() -> SearchStrategy[object]:
	return from_type(object).filter(lambda x: not isinstance(x, bytes))


def codepoint_ranges() -> SearchStrategy[range]:
	return tuples(codepoints(), codepoints()).map(to_range)


def byte_codepoint_ranges() -> SearchStrategy[range]:
	return tuples(byte_codepoints(), byte_codepoints()).map(to_range)


def character_intervals() -> SearchStrategy[CharacterInterval]:
	return codepoint_ranges().map(CharacterInterval.from_codepoint_range)


def byte_intervals() -> SearchStrategy[ByteInterval]:
	return byte_codepoint_ranges().map(ByteInterval.from_codepoint_range)
