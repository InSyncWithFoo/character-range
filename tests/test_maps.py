import re
import string
from collections.abc import Callable
from itertools import chain, product
from typing import Any, NamedTuple

import pytest
from typing_extensions import Never

from character_range.maps import (
	ByteInterval, ByteMap,
	CharacterInterval, CharacterMap,
	ConfigurationConflict,
	InvalidChar, InvalidIndex, NoIntervals,
	OverlappingIntervals
)
from . import generate_non_overlapping_intervals, make_map


_single_byte = re.compile(b'.', flags = re.S)


def _raise(exception_type: type[Exception]) -> Callable[[Any, ...], Never]:
	def _raiser(*_args: object, **_kwargs: object) -> Never:
		raise exception_type
	
	return _raiser


def _no_op(*_args: object, **_kwargs: object) -> None:
	pass


def _return_minus_1(_char):
	return -1


_MAX_UNICODE_CODEPOINT = 0x10FFFF


def _return_big_int(_char):
	return _MAX_UNICODE_CODEPOINT + 1


class _MapArguments(NamedTuple):
	intervals: list[CharacterInterval] | list[ByteInterval]
	lookup_char: Callable[..., Any]
	lookup_index: Callable[..., Any]


@pytest.mark.parametrize('arguments, expected_error', [
	(([], (None, None)), NoIntervals),
	(([CharacterInterval('a', 'b')], (None, chr)), ConfigurationConflict),
	(([CharacterInterval('a', 'b')], (ord, None)), ConfigurationConflict),
	(
		(
			[CharacterInterval('a', 'c'), CharacterInterval('b', 'd')],
			(None, None)
		),
		OverlappingIntervals
	),
	(
		(
			[CharacterInterval('a', 'c'), CharacterInterval('b', 'd')],
			(ord, chr)
		),
		OverlappingIntervals
	),
	(
		(
			[CharacterInterval('a', 'c'), ByteInterval(b'd', b'f')],
			(None, None)
		),
		ConfigurationConflict
	)
])
def test_map_invalid(arguments, expected_error):
	assert issubclass(expected_error, ValueError)
	
	intervals, (lookup_char, lookup_index) = arguments
	
	with pytest.raises(expected_error):
		_ = CharacterMap(
			intervals,
			lookup_char = lookup_char,
			lookup_index = lookup_index
		)


@pytest.mark.parametrize('intervals', chain.from_iterable([
	[
		[CharacterInterval('a', 'd'), CharacterInterval('e', 'z')],
		[
			CharacterInterval('\x04', '\u0147'),
			CharacterInterval('\u0FD3', '\u0FF9'),
			CharacterInterval('\U00010000', '\U000100FF')
		]
	],
	(list(generate_non_overlapping_intervals('character')) for _ in range(10)),
	(list(generate_non_overlapping_intervals('byte')) for _ in range(10))
]))
def test_map_len_custom_lookup(intervals):
	if len(intervals) <= 10:
		configurations = {}
	else:
		configurations = dict(lookup_char = ord, lookup_index = chr)
	
	character_map = CharacterMap(intervals, **configurations)
	
	assert len(character_map) == sum(len(interval) for interval in intervals)


@pytest.mark.parametrize('constructor, intervals', [
	*product(
		[CharacterMap],
		[
			list(generate_non_overlapping_intervals('character'))
			for _ in range(10)
		]
	),
	*product(
		[ByteMap],
		[
			list(generate_non_overlapping_intervals('byte'))
			for _ in range(10)
		]
	)
])
def test_map_repr(constructor, intervals):
	result = repr(constructor(intervals, ord, chr))
	
	assert constructor.__name__ in result
	assert ''.join(str(interval) for interval in intervals) in result


@pytest.mark.parametrize('character_or_byte_map, item_and_expected', [
	*product(
		[
			CharacterMap.ASCII_LETTERS,
			CharacterMap([
				CharacterInterval('a', 'z'),
				CharacterInterval('A', 'Z')
			])
		],
		[
			*product(
				['a', 'm', 'z', 'A', 'N', 'z', 0, 13, 25, 26, 39],
				[True]
			),
			*product(
				[52, '0', b'0', b'a', '#', '^$', -1, 3.14, object()],
				[False]
			)
		]
	),
	*product(
		[
			ByteMap.ASCII_LETTERS,
			ByteMap([
				ByteInterval(b'a', b'z'),
				ByteInterval(b'A', b'Z')
			])
		],
		[
			*product(
				[b'a', b'm', b'z', b'A', b'N', b'z', 0, 13, 25, 26, 39],
				[True]
			),
			*product(
				[52, '0', b'0', 'a', b'#', b'^$', -1, 3.14, object()],
				[False]
			)
		]
	)
])
def test_map_contains(character_or_byte_map, item_and_expected):
	item, expected = item_and_expected
	
	assert (item in character_or_byte_map) is expected


@pytest.mark.parametrize('arguments', [
	_MapArguments(*arguments)
	for arguments in product(
		[
			[CharacterInterval('\x44', '\x55')],
			[ByteInterval(b'\x44', b'\x55')]
		],
		[_raise(ValueError), _raise(LookupError), _no_op],
		[_raise(ValueError), _raise(LookupError), _no_op]
	)
])
@pytest.mark.parametrize('item, expected', [
	('\x44', False),
	('\x55', False),
	(b'\x44', False),
	(b'\x55', False)
])
def test_map_contains_exception_handling(
	arguments: _MapArguments, item, expected
):
	character_or_byte_map = make_map(*arguments)
	
	assert (item in character_or_byte_map) is expected


@pytest.mark.parametrize('character_or_byte_map, index_and_char', [
	(ByteMap.ASCII, (b'\x54', 0x54)),
	(CharacterMap.ASCII, (0x18, '\x18')),
	(CharacterMap.UNICODE, (0x4321, '\u4321')),
	*product(
		[CharacterMap.ASCII_LETTERS],
		[
			(True, 'b'),
			*enumerate(string.ascii_letters)
		]
	),
	*product(
		[CharacterMap([CharacterInterval('\uDE6A', '\uDF4C')])],
		[*enumerate(CharacterInterval('\uDE6A', '\uDF4C'))]
	),
	*product(
		[ByteMap.ASCII_LETTERS],
		[
			(False, b'a'),
			*enumerate(
				_single_byte.findall(string.ascii_letters.encode('utf-8'))
			)
		]
	)
])
def test_map_getitem(character_or_byte_map, index_and_char):
	index, char = index_and_char
	
	assert character_or_byte_map[index] == char
	assert character_or_byte_map[char] == index


@pytest.mark.parametrize('character_or_byte_map, item_and_expected_error', [
	(CharacterMap.ASCII_LETTERS, (b'foo', TypeError)),
	(ByteMap.ASCII_LETTERS, ('foo', TypeError)),
	(CharacterMap.ASCII, ('\u0100', ValueError)),
	*product(
		[CharacterMap.ASCII_LETTERS, ByteMap.ASCII_LETTERS],
		product(
			[3.14, object(), int.to_bytes],
			[TypeError]
		)
	),
	*product(
		[CharacterMap.ASCII_LETTERS],
		[
			('0', LookupError),
			(-1, IndexError),
			(52, IndexError),
		]
	),
	*product(
		[CharacterMap.ASCII, ByteMap.ASCII],
		[(0x100, IndexError)]
	)
])
def test_map_getitem_invalid(character_or_byte_map, item_and_expected_error):
	item, expected_error = item_and_expected_error
	
	with pytest.raises(expected_error):
		_ = character_or_byte_map[item]


@pytest.mark.parametrize('arguments, item_and_expected_error', [
	*product(
		product(
			[[CharacterInterval('\uA04F', '\uBDE8')]],
			[_return_minus_1, _return_big_int],
			[_no_op]
		),
		[
			('a', InvalidIndex),
			(1, InvalidChar)
		]
	),
	*product(
		product(
			[[ByteInterval(b'\x4F', b'\xA0')]],
			[_return_minus_1, _return_big_int],
			[_no_op]
		),
		[
			(b'a', InvalidIndex),
			(1, InvalidChar)
		]
	)
])
def test_map_getitem_invalid_return_value(arguments, item_and_expected_error):
	item, expected_error = item_and_expected_error
	character_or_byte_map = make_map(*arguments)
	
	with pytest.raises(expected_error):
		_ = character_or_byte_map[item]


@pytest.mark.parametrize('this, that, expected', [
	(
		CharacterMap.ASCII_LOWERCASE,
		CharacterMap.ASCII_UPPERCASE,
		CharacterMap.ASCII_LETTERS
	),
	(
		CharacterMap.ASCII_DIGITS,
		CharacterInterval('a', 'f'),
		CharacterMap.LOWERCASE_HEX_DIGITS
	),
	(
		CharacterMap.ASCII_DIGITS,
		CharacterInterval('A', 'F'),
		CharacterMap.UPPERCASE_HEX_DIGITS
	),
	(
		CharacterMap.ASCII_DIGITS,
		CharacterMap.ASCII_LOWERCASE,
		CharacterMap.LOWERCASE_BASE_36
	),
	(
		CharacterMap.ASCII_DIGITS,
		CharacterMap.ASCII_UPPERCASE,
		CharacterMap.UPPERCASE_BASE_36
	),
	(
		ByteMap.ASCII_LOWERCASE,
		ByteMap.ASCII_UPPERCASE,
		ByteMap.ASCII_LETTERS
	),
	(
		ByteMap.ASCII_DIGITS,
		ByteInterval(b'a', b'f'),
		ByteMap.LOWERCASE_HEX_DIGITS
	),
	(
		ByteMap.ASCII_DIGITS,
		ByteInterval(b'A', b'F'),
		ByteMap.UPPERCASE_HEX_DIGITS
	),
	(
		ByteMap.ASCII_DIGITS,
		ByteMap.ASCII_LOWERCASE,
		ByteMap.LOWERCASE_BASE_36
	),
	(
		ByteMap.ASCII_DIGITS,
		ByteMap.ASCII_UPPERCASE,
		ByteMap.UPPERCASE_BASE_36
	)
])
def test_map_add_and_eq(this, that, expected):
	combined = this + that
	
	if isinstance(that, CharacterInterval | ByteInterval):
		other_map = make_map([that])
		assert combined == this + other_map
	else:
		assert this.intervals + that.intervals == combined.intervals
	
	assert combined == expected
	assert combined.intervals == expected.intervals


@pytest.mark.parametrize('this, that, expected_error', [
	(CharacterMap.ASCII, {}, TypeError),
	(ByteMap.ASCII, CharacterMap.NON_ASCII, ConfigurationConflict),
	(CharacterMap.ASCII, CharacterMap.NON_ASCII, ConfigurationConflict)
])
def test_add_invalid(this, that, expected_error):
	with pytest.raises(expected_error):
		_ = this + that


@pytest.mark.parametrize('map_class', [
	CharacterMap,
	ByteMap
])
def test_class_members(map_class):
	members = map_class.members
	
	assert isinstance(members, tuple)
	assert all(isinstance(member, map_class) for member in members)


@pytest.mark.parametrize('map_class, member_name_and_expected', [
	*product(
		[CharacterMap],
		[
			('ASCII_LOWERCASE', CharacterMap([CharacterInterval('a', 'z')])),
			('ASCII_UPPERCASE', CharacterMap([CharacterInterval('A', 'Z')])),
			(
				'ASCII_LETTERS',
				CharacterMap.ASCII_LOWERCASE + CharacterMap.ASCII_UPPERCASE
			),
			('ASCII_DIGITS', CharacterMap([CharacterInterval('0', '9')])),
			(
				'LOWERCASE_HEX_DIGITS',
				CharacterMap([
					CharacterInterval('0', '9'),
					CharacterInterval('a', 'f')
				])
			),
			(
				'UPPERCASE_HEX_DIGITS',
				CharacterMap([
					CharacterInterval('0', '9'),
					CharacterInterval('A', 'F')
				])
			),
			(
				'LOWERCASE_BASE_36',
				CharacterMap([
					CharacterInterval('0', '9'),
					CharacterInterval('a', 'z')
				])
			),
			(
				'UPPERCASE_BASE_36',
				CharacterMap([
					CharacterInterval('0', '9'),
					CharacterInterval('A', 'Z')
				])
			),
			('ASCII', CharacterMap([CharacterInterval('\x00', '\xFF')])),
			(
				'NON_ASCII',
				CharacterMap([CharacterInterval('\u0100', '\U0010FFFF')])
			),
			(
				'UNICODE',
				CharacterMap([CharacterInterval('\x00', '\U0010FFFF')])
			)
		]
	),
	*product(
		[ByteMap],
		[
			('ASCII_LOWERCASE', ByteMap([ByteInterval(b'a', b'z')])),
			('ASCII_UPPERCASE', ByteMap([ByteInterval(b'A', b'Z')])),
			(
				'ASCII_LETTERS',
				ByteMap.ASCII_LOWERCASE + ByteMap.ASCII_UPPERCASE
			),
			('ASCII_DIGITS', ByteMap([ByteInterval(b'0', b'9')])),
			(
				'LOWERCASE_HEX_DIGITS',
				ByteMap.ASCII_DIGITS + ByteInterval(b'a', b'f')
			),
			(
				'UPPERCASE_HEX_DIGITS',
				ByteMap.ASCII_DIGITS + ByteInterval(b'A', b'F')
			),
			(
				'LOWERCASE_BASE_36',
				ByteMap.ASCII_DIGITS + ByteMap.ASCII_LOWERCASE
			),
			(
				'UPPERCASE_BASE_36',
				ByteMap.ASCII_DIGITS + ByteMap.ASCII_UPPERCASE
			),
			('ASCII', ByteMap([ByteInterval(b'\x00', b'\xFF')]))
		]
	),
])
def test_prebuilt_member(map_class, member_name_and_expected):
	member_name, expected = member_name_and_expected
	
	assert isinstance(map_class[member_name], map_class)
	assert map_class[member_name] == expected
