import random
from collections.abc import Callable, Iterator, Reversible
from functools import partial
from itertools import product
from typing import Any, TypeVar

import pytest
from _pytest.mark import ParameterSet
from hypothesis import assume, given
from hypothesis.strategies import just, one_of, tuples
from typing_extensions import Literal

from character_range import character_range, UnrecognizedEndpointTypes
from character_range.intervals import (
	ByteInterval, CharacterInterval,
	Interval, InvalidCodepointRange,
	InvalidIntervalDirection,
	NotAByte, NotACharacter
)
from . import iife, make_interval_from_endpoints
from .strategies import (
	byte_codepoint_ranges, byte_endpoints, byte_intervals,
	character_endpoints, character_intervals, codepoint_ranges,
	non_byte_endpoints, non_bytes, non_character_endpoints, non_strings,
	range_and_random_item, tupled_with_class, tupled_with_invalid_index
)


_I = TypeVar('_I', bound = Interval)
_C = TypeVar('_C', str, bytes)

_intersect_methods = [
	pytest.param(lambda a, b: a & b, id = 'a.__and__'),
	pytest.param(lambda a, b: b & a, id = 'b.__and__'),
	pytest.param(lambda a, b: a.intersects(b), id = 'a.intersects'),
	pytest.param(lambda a, b: b.intersects(a), id = 'b.intersects'),
]


@iife
class _Slice:
	r'''
	Singleton used to define :class:`slice` objects
	using slice notation:
	
		>>> _Slice[1:3]
		slice(1, 3, None)
	'''
	
	def __getitem__(self, item: slice):
		return item


def _describe(value: int | None, /) -> str:
	if value is None:
		return 'default'
	
	if value > 0:
		return 'positive'
	
	if value < 0:
		return 'negative'
	
	return 'zero'


def _slice_test_parameter_set(
	interval: Interval, item: slice,
	expected: tuple[int, int] | type[ValueError]
) -> ParameterSet:
	
	step = item.step
	
	# if isinstance(expected, Interval):
	description = (
		f'{_describe(item.start)} start, '
		f'{_describe(item.stop)} stop, '
		f'{step = } - '
		f'{type(interval).__name__}'
	)
	
	return pytest.param(interval, item, expected, id = description)


def _to_integral_endpoints(start: str, stop: str) -> tuple[int, int]:
	return ord(start), ord(stop)


def _slice_tests(
	endpoints: tuple[str, str],
	item: slice,
	expected_endpoints: tuple[str, str]
) -> Iterator[ParameterSet]:
	start, end = _to_integral_endpoints(*endpoints)
	expected_start, expected_end = _to_integral_endpoints(*expected_endpoints)
	
	for step in (None, 1):
		new_item = slice(item.start, item.stop, step)
		
		for interval_type in ('character', 'byte'):
			interval_type: Literal['character', 'byte']
			make_interval = partial(
				make_interval_from_endpoints,
				interval_type = interval_type
			)
			
			interval = make_interval(start, end)
			expected = make_interval(expected_start, expected_end)
			
			yield _slice_test_parameter_set(interval, new_item, expected)


def _slice_invalid_tests(
	endpoints: tuple[str, str],
	item: slice,
):
	start, end = _to_integral_endpoints(*endpoints)
	
	for step in (-1, 0, 2):
		new_item = slice(item.start, item.stop, step)
		
		if step == 0:
			expected = ValueError
		else:
			expected = InvalidCodepointRange
		
		for interval_type in ('character', 'byte'):
			interval_type: Literal['character', 'byte']
			interval = make_interval_from_endpoints(start, end, interval_type)
			
			yield pytest.param(
				interval, new_item, expected,
				id = (
					f'{_describe(item.start)} start, '
					f'{_describe(item.stop)} stop, '
					f'{step = } - '
					f'{interval_type}'
				)
			)


@pytest.mark.parametrize('exception', [
	NotAByte,
	NotACharacter,
	InvalidIntervalDirection
])
def test_exception_types(exception):
	assert issubclass(exception, ValueError)


@given(
	one_of([
		tuples(non_character_endpoints(), character_endpoints()),
		tuples(character_endpoints(), non_character_endpoints()),
		tuples(non_character_endpoints(), non_character_endpoints())
	])
)
def test_interval_not_a_character(endpoints):
	with pytest.raises(NotACharacter):
		_ = CharacterInterval(*endpoints)


@given(
	one_of([
		tuples(non_byte_endpoints(), byte_endpoints()),
		tuples(byte_endpoints(), non_byte_endpoints()),
		tuples(non_byte_endpoints(), non_byte_endpoints())
	])
)
def test_interval_not_a_byte(endpoints):
	with pytest.raises(NotAByte):
		_ = ByteInterval(*endpoints)


@given(
	one_of([
		tuples(
			tuples(character_endpoints(), character_endpoints()) \
				.map(sorted).map(reversed),
			just(CharacterInterval)
		),
		tuples(
			tuples(byte_endpoints(), byte_endpoints()) \
				.map(sorted).map(reversed),
			just(ByteInterval)
		)
	])
)
def test_interval_invalid_direction(endpoints_and_class):
	(start, end), interval_class = endpoints_and_class
	
	assume(start != end)
	
	with pytest.raises(InvalidIntervalDirection):
		_ = interval_class(start, end)


@pytest.mark.parametrize('endpoints, expected', [
	(('a', 'z'), CharacterInterval),
	((b'a', b'z'), ByteInterval),
	(('\x00', '\xFF'), CharacterInterval),
	((b'\x00', b'\xFF'), ByteInterval),
	(('a', 'a'), CharacterInterval),
	((b'a', b'a'), ByteInterval),
	(('\x00', '\x00'), CharacterInterval),
	((b'\x00', b'\x00'), ByteInterval),
	(('\uD800', '\uDBFF'), CharacterInterval),
	(('\uDC00', '\uDFFF'), CharacterInterval),
	(('\U00010000', '\U0010FFFF'), CharacterInterval)
])
def test_functional_alias(endpoints, expected):
	interval = character_range(*endpoints)
	
	assert isinstance(interval, expected)


@given(
	one_of([
		tuples(non_strings(), character_endpoints()),
		tuples(character_endpoints(), non_strings()),
		tuples(non_bytes(), byte_endpoints()),
		tuples(byte_endpoints(), non_bytes())
	])
)
def test_functional_alias_invalid(endpoints):
	with pytest.raises(UnrecognizedEndpointTypes):
		_ = character_range(*endpoints)


@given(
	one_of([
		tuples(
			tuples(character_endpoints(), character_endpoints()).map(sorted),
			just(CharacterInterval)
		),
		tuples(
			tuples(byte_endpoints(), byte_endpoints()).map(sorted),
			just(ByteInterval)
		)
	])
)
def test_interval_hashability(start_end_class):
	(start, end), interval_class = start_end_class
	
	interval_1 = interval_class(start, end)
	interval_2 = interval_class(start, end)
	
	assert hash(interval_1) == hash(interval_2)
	assert {interval_1, interval_2} == {interval_1}

@pytest.mark.parametrize('constructor, args', [
	*product(
		[CharacterInterval],
		[
			('a', 'b', 'a-b'),
			('a', 'a', 'a'),
			('\\', '\\', r'\\'),
			('-', '-', r'\-'),
			('-', '\\', r'\--\\'),
			('\x0C', '\\', r'\x0C-\\'),
			('\x7f', '\x7F', r'\x7F'),
			('\x7F', '\x7f', r'\x7F'),
			('\x0d', '\x41', r'\x0D-A'),
			('\uf892', '\uf893', r'\uF892-\uF893'),
			('\xFf', '\U0010fffD', r'\xFF-\U0010FFFD'),
			('\uAbCd', '\U0010FFFd', r'\uABCD-\U0010FFFD'),
		]
	),
	*product(
		[ByteInterval],
		[
			(b'a', b'b', 'a-b'),
			(b'a', b'a', 'a'),
			(b'\\', b'\\', r'\\'),
			(b'\x0c', b'\\', r'\x0C-\\'),
			(b'\x0C', b'\\', r'\x0C-\\'),
			(b'\x7f', b'\x7F', r'\x7F'),
			(b'\x7F', b'\x7f', r'\x7F'),
			(b'\x0a', b'\x41', r'\x0A-A')
		]
	)
])
def test_interval_repr(constructor, args):
	start, end, expected = args
	interval = constructor(start, end)
	
	representation = repr(interval)
	stringified = str(interval)
	
	assert constructor.__name__ in representation
	assert stringified == expected
	assert stringified in representation


@given(
	one_of([
		tuples(codepoint_ranges(), just(CharacterInterval)),
		tuples(byte_codepoint_ranges(), just(ByteInterval))
	])
)
def test_interval_to_range_and_len(range_and_class):
	from_range, interval_class = range_and_class
	
	interval = interval_class.from_codepoint_range(from_range)
	to_range = interval.to_codepoint_range()
	
	assert len(from_range) == len(interval) == len(to_range)
	assert from_range == to_range


@pytest.mark.parametrize('interval', [
	CharacterInterval('a', 'z'),
	ByteInterval(b'a', b'z'),
	CharacterInterval('\x4F', '\x7F'),
	ByteInterval(b'\x4F', b'\x7F'),
	CharacterInterval('\uD800', '\uDBFF'),
	CharacterInterval('\uDC00', '\uDFFF'),
	CharacterInterval('\x00', '\U0010FFFF'),
	ByteInterval(b'\x00', b'\xFF')
])
def test_interval_iterability(interval):
	for value, char_code in zip(interval, interval.to_codepoint_range()):
		assert ord(value) == char_code


@given(
	one_of([
		codepoint_ranges() \
			.flatmap(range_and_random_item) \
			.map(tupled_with_class(CharacterInterval)),
		byte_codepoint_ranges() \
			.flatmap(range_and_random_item) \
			.map(tupled_with_class(ByteInterval))
	])
)
def test_interval_contains(range_item_class):
	(codepoint_range, item), interval_class = range_item_class
	
	interval = interval_class.from_codepoint_range(codepoint_range)
	interval_element = interval_class._make_element(item)
	
	assert interval_element in interval


@pytest.mark.parametrize('this, that, expected', [
	pytest.param(
		CharacterInterval('a', 'z'),
		CharacterInterval('a', 'z'),
		True,
		id = 'CharacterInterval'
	),
	pytest.param(
		ByteInterval(b'A', b'Z'),
		ByteInterval(b'A', b'Z'),
		True,
		id = 'ByteInterval'
	),
	pytest.param(
		CharacterInterval('a', 'z'),
		ByteInterval(b'A', b'Z'),
		False,
		id = 'Different type, different codepoints'
	),
	pytest.param(
		CharacterInterval('a', 'z'),
		ByteInterval(b'a', b'z'),
		False,
		id = 'Different type, same codepoints'
	)
])
def test_interval_eq(this, that, expected):
	assert (this == that) is expected


@given(one_of([character_intervals(), byte_intervals()]))
def test_interval_getitem_index(interval):
	codepoint_range = interval.to_codepoint_range()
	sample_size = min(10, len(codepoint_range))
	indices = random.sample(range(len(codepoint_range)), sample_size)
	
	for index in [0, *indices, len(codepoint_range) - 1]:
		if isinstance(interval, CharacterInterval):
			element = chr(codepoint_range[index])
		else:
			element = codepoint_range[index].to_bytes(1, 'big')
		
		assert element == interval[index]


@given(
	one_of([character_intervals(), byte_intervals()]) \
		.flatmap(tupled_with_invalid_index)
)
def test_interval_getitem_invalid_index(interval_and_index):
	interval, index = interval_and_index
	
	with pytest.raises(IndexError):
		_ = interval[index]


@pytest.mark.parametrize('interval, item, expected', [
	*_slice_tests(('a', 'z'), _Slice[1:10], ('b', 'j')),
	*_slice_tests(('a', 'z'), _Slice[1:-1], ('b', 'y')),
	*_slice_tests(('a', 'z'), _Slice[1:], ('b', 'z')),
	*_slice_tests(('a', 'z'), _Slice[0:1], ('a', 'a')),
	*_slice_tests(('a', 'z'), _Slice[0:10], ('a', 'j')),
	*_slice_tests(('a', 'z'), _Slice[0:-1], ('a', 'y')),
	*_slice_tests(('a', 'z'), _Slice[0:], ('a', 'z')),
	*_slice_tests(('a', 'z'), _Slice[-10:20], ('q', 't')),
	*_slice_tests(('a', 'z'), _Slice[-10:-1], ('q', 'y')),
	*_slice_tests(('a', 'z'), _Slice[-10:], ('q', 'z')),
	*_slice_tests(('a', 'z'), _Slice[:1], ('a', 'a')),
	*_slice_tests(('a', 'z'), _Slice[:10], ('a', 'j')),
	*_slice_tests(('a', 'z'), _Slice[:-1], ('a', 'y')),
	*_slice_tests(('a', 'z'), _Slice[:], ('a', 'z'))
])
def test_interval_getitem_slice(interval, item, expected):
	assert interval[item] == expected


@pytest.mark.parametrize('interval, item, expected', [
	*_slice_invalid_tests(('a', 'z'), _Slice[20:10]),
	*_slice_invalid_tests(('a', 'z'), _Slice[10:0]),
	*_slice_invalid_tests(('a', 'z'), _Slice[20:-10]),
	*_slice_invalid_tests(('a', 'z'), _Slice[30:]),
	*_slice_invalid_tests(('a', 'z'), _Slice[0:30]),
	*_slice_invalid_tests(('a', 'z'), _Slice[0:0]),
	*_slice_invalid_tests(('a', 'z'), _Slice[0:-30]),
	*_slice_invalid_tests(('a', 'z'), _Slice[-10:10]),
	*_slice_invalid_tests(('a', 'z'), _Slice[-10:0]),
	*_slice_invalid_tests(('a', 'z'), _Slice[-10:-20]),
	*_slice_invalid_tests(('a', 'z'), _Slice[-10:]),
	*_slice_invalid_tests(('a', 'z'), _Slice[:30]),
	*_slice_invalid_tests(('a', 'z'), _Slice[:0]),
	*_slice_invalid_tests(('a', 'z'), _Slice[:-30])
])
def test_interval_getitem_invalid_slice(interval, item, expected):
	with pytest.raises(expected):
		_ = interval[item]


@given(one_of([character_intervals(), byte_intervals()]))
def test_interval_reversed(interval: Interval):
	assert isinstance(interval, Reversible)
	
	limit = min(len(interval), random.randint(10, 15))
	
	for index, element in enumerate(reversed(interval)):
		assert element in interval
		assert element == interval[~index]
		
		if index > limit:
			break


@pytest.mark.parametrize('this, that, expected', [
	(CharacterInterval('a', 'e'), CharacterInterval('g', 'l'), False),
	(CharacterInterval('a', 'e'), CharacterInterval('e', 'l'), True),
	(CharacterInterval('a', 'e'), CharacterInterval('d', 'l'), True),
	(ByteInterval(b'a', b'e'), ByteInterval(b'g', b'l'), False),
	(ByteInterval(b'a', b'e'), ByteInterval(b'e', b'l'), True),
	(ByteInterval(b'a', b'e'), ByteInterval(b'd', b'l'), True)
])
@pytest.mark.parametrize('method', _intersect_methods)
def test_interval_intersects(this, that, expected, method):
	method: Callable[[Any, Any], bool]
	
	assert method(this, that) is expected


@pytest.mark.parametrize('this, that, expected_error', [
	(CharacterInterval('a', 'e'), ByteInterval(b'c', b'g'), TypeError),
	(ByteInterval(b'a', b'e'), CharacterInterval('c', 'g'), TypeError)
])
@pytest.mark.parametrize('method', _intersect_methods)
def test_interval_intersects_invalid(method, this, that, expected_error):
	method: Callable[[Any, Any], bool]
	
	with pytest.raises(expected_error):
		method(this, that)
