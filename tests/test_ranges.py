import string
from itertools import product

import pytest

from character_range import (
	ByteMap,
	bytes_range, BytesRange,
	CharacterInterval, CharacterMap,
	string_range, StringRange
)
from character_range.maps import ByteInterval, IndexMap
from character_range.ranges import (
	InvalidEndpoints,
	InvalidRangeDirection
)


def _to_str(value):
	return value if isinstance(value, str) else value.decode('latin-1')


def _to_bytes(value):
	return value if isinstance(value, bytes) else value.encode('latin-1')


def _to_list_of_str(value, /):
	return [_to_str(element) for element in value]


def _to_list_of_bytes(value, /):
	return [_to_bytes(element) for element in value]


def _make_range(element_type, start, end, index_map):
	if element_type is str:
		functional_alias = string_range
		start, end = _to_str(start), _to_str(end)
		map_class = CharacterMap
	else:
		functional_alias = bytes_range
		start, end = _to_bytes(start), _to_bytes(end)
		map_class = ByteMap
	
	if isinstance(index_map, str):
		index_map = map_class[index_map.upper().replace(' ', '_')]
	
	return functional_alias(start, end, index_map)


def _make_ranges(*args):
	return _make_range(str, *args), _make_range(bytes, *args)


def _make_iter_testcase_arguments(
	element_type,
	start, end, index_map, expected
):
	if element_type is str:
		return (
			_make_range(str, start, end, index_map),
			_to_list_of_str(expected)
		)
	
	return (
		_make_range(bytes, start, end, index_map),
		_to_list_of_bytes(expected)
	)


def _make_iter_testcases(*args, name: str):
	for_str = _make_iter_testcase_arguments(str, *args)
	for_bytes = _make_iter_testcase_arguments(bytes, *args)
	
	return (
		pytest.param(*for_str, id = f'{name} - str'),
		pytest.param(*for_bytes, id = f'{name} - bytes')
	)


@pytest.mark.parametrize('constructor, start, end, index_map, expected_error', [
	pytest.param(
		StringRange, '', 'foo', CharacterMap.ASCII_LOWERCASE,
		InvalidEndpoints,
		id = 'empty start'
	),
	pytest.param(
		StringRange, 'bar', '', CharacterMap.ASCII_LOWERCASE,
		InvalidEndpoints,
		id = 'empty end'
	),
	pytest.param(
		StringRange, '', '', CharacterMap.ASCII_LOWERCASE,
		InvalidEndpoints,
		id = 'empty start and end'
	),
	pytest.param(
		StringRange, 'bar', 'foo', ByteMap.ASCII_LOWERCASE,
		InvalidEndpoints,
		id = 'str start, str end, bytes map'
	),
	pytest.param(
		BytesRange, b'bar', b'foo', CharacterMap.ASCII_LOWERCASE,
		InvalidEndpoints,
		id = 'bytes start, bytes end, str map'
	),
	pytest.param(
		StringRange, '8AR', '931', CharacterMap.ASCII_DIGITS,
		InvalidEndpoints,
		id = 'start not found in map'
	),
	pytest.param(
		StringRange, '010', 'F00', CharacterMap.ASCII_DIGITS,
		InvalidEndpoints,
		id = 'end not found in map'
	),
	pytest.param(
		StringRange, 'BAR', 'FOO', CharacterMap.ASCII_DIGITS,
		InvalidEndpoints,
		id = 'start and end not found in map'
	),
	pytest.param(
		StringRange, 'foo', 'bar', CharacterMap.ASCII_LOWERCASE,
		InvalidRangeDirection,
		id = 'start > end lexicographically'
	),
	pytest.param(
		StringRange, 'barz', 'foo', CharacterMap.ASCII_LOWERCASE,
		InvalidRangeDirection,
		id = 'start > end length-wise'
	)
])
def test_range_invalid(constructor, start, end, index_map, expected_error):
	with pytest.raises(expected_error):
		_ = constructor(start, end, index_map)  # noqa


@pytest.mark.parametrize('string_or_bytes_range, expected', [
	(
		StringRange('\x00', '\U0010FFFF', CharacterMap.UNICODE),
		0x10FFFF + 1
	),
	(
		BytesRange(b'\x00', b'\xFF', ByteMap.ASCII),
		0xFF + 1
	),
	(
		StringRange('\x00' * 3, '\U0010FFFF' * 3, CharacterMap.UNICODE),
		(0x10FFFF + 1) ** 3
	),
	(
		BytesRange(b'\x00' * 5, b'\xFF' * 5, ByteMap.ASCII),
		(0xFF + 1) ** 5
	),
	*product(
		[
			StringRange('03FD9', '16C74', CharacterMap.UPPERCASE_HEX_DIGITS),
			BytesRange(b'03FD9', b'16C74', ByteMap.UPPERCASE_HEX_DIGITS)
		],
		[0x16C74 - 0x3FD9 + 1]
	),
	*product(
		[
			StringRange('3FD9', '16C74', CharacterMap.UPPERCASE_HEX_DIGITS),
			BytesRange(b'3FD9', b'16C74', ByteMap.UPPERCASE_HEX_DIGITS)
		],
		[0x16C74 + (0xFFFF + 1) - 0x3FD9 + 1]
	),
	*product(
		[
			StringRange('z', 'aaaaa', CharacterMap.ASCII_LOWERCASE),
			BytesRange(b'z', b'aaaaa', ByteMap.ASCII_LOWERCASE)
		],
		[26 ** 2 + 26 ** 3 + 26 ** 4 + 2]
	)
])
def test_range_len(string_or_bytes_range, expected):
	assert len(string_or_bytes_range) == expected


@pytest.mark.parametrize('string_or_bytes_range, expected', [
	*_make_iter_testcases(
		'a', 'z', 'ASCII lowercase', string.ascii_lowercase,
		name = 'ASCII lowercase',
	),
	*_make_iter_testcases(
		'A', 'Z', 'ASCII uppercase', string.ascii_uppercase,
		name = 'ASCII uppercase',
	),
	*_make_iter_testcases(
		'0', '000', 'ASCII digits',
		[
			'0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
			*(str(number).rjust(2, '0') for number in range(100)),
			'000'
		],
		name = 'decimal'
	),
	*_make_iter_testcases(
		'\x00', '\x19', 'ASCII',
		list(CharacterInterval('\x00', '\x19')),
		name = 'non-printables'
	),
	*_make_iter_testcases(
		r'\x00', r'\x19', 'ASCII',
		[
			*(
				fr'\x0{chr(codepoint)}'
				for codepoint in range(ord('0'), 0xFF + 1)
			),
			*(
				fr'\x1{chr(codepoint)}'
				for codepoint in range(0, ord('0'))
			),
			r'\x10', r'\x11', r'\x12', r'\x13', r'\x14',
			r'\x15', r'\x16', r'\x17', r'\x18', r'\x19'
		],
		name = 'escape sequences'
	),
	*_make_iter_testcases(
		'zz', 'aaa', 'ASCII lowercase',
		['zz', 'aaa'],
		name = 'n * (base - 1) to (n + 1) * 0'
	),
	*_make_iter_testcases(
		'abc', 'acc', 'ASCII lowercase',
		[
			'abc', 'abd', 'abe', 'abf', 'abg', 'abh', 'abi', 'abj', 'abk',
			'abl', 'abm', 'abn', 'abo', 'abp', 'abq', 'abr', 'abs', 'abt',
			'abu', 'abv', 'abw', 'abx', 'aby', 'abz', 'aca', 'acb', 'acc'
		],
		name = 'a ** base + b to (a + 1) ** base + b'
	),
	*_make_iter_testcases(
		'yp', 'abc', 'ASCII lowercase',
		[
			'yp', 'yq', 'yr', 'ys', 'yt', 'yu', 'yv', 'yw', 'yx', 'yy', 'yz',
			'za', 'zb', 'zc', 'zd', 'ze', 'zf', 'zg', 'zh', 'zi', 'zj', 'zk',
			'zl', 'zm', 'zn', 'zo', 'zp', 'zq', 'zr', 'zs', 'zt', 'zu', 'zv',
			'zw', 'zx', 'zy', 'zz', 'aaa', 'aab', 'aac', 'aad', 'aae', 'aaf',
			'aag', 'aah', 'aai', 'aaj', 'aak', 'aal', 'aam', 'aan', 'aao',
			'aap', 'aaq', 'aar', 'aas', 'aat', 'aau', 'aav', 'aaw', 'aax',
			'aay', 'aaz', 'aba', 'abb', 'abc'
		],
		name = 'both of the above'
	),
	pytest.param(
		BytesRange(b'\x00\x00', b'\xFF\xFF', ByteMap.ASCII),
		[
			b''.join(pair)
			for pair in product(ByteInterval(b'\x00', b'\xFF'), repeat = 2)
		],
		id = 'byte >= 0x80'
	)
])
def test_range_iterability(string_or_bytes_range, expected):
	elements = list(string_or_bytes_range)
	
	assert elements == expected
	assert len(string_or_bytes_range) == len(elements)


@pytest.mark.parametrize('string_or_bytes_range', [
	*_make_ranges('a', 'z', 'ASCII lowercase'),
	*_make_ranges('\x00', '\xFF', 'ASCII'),
	*_make_ranges('fOo', 'BaRz', 'ASCII letters')
])
def test_range_repr(string_or_bytes_range):
	representation = repr(string_or_bytes_range)
	
	assert string_or_bytes_range.__class__.__name__ in representation
	assert repr(string_or_bytes_range.start) in representation
	assert repr(string_or_bytes_range.end) in representation


@pytest.mark.parametrize('string_or_bytes_range', [
	*_make_ranges('a', 'z', 'ASCII lowercase'),
	*_make_ranges('\x00', '\xFF', 'ASCII'),
	*_make_ranges('fOo', 'BaRz', 'ASCII letters')
])
def test_range_map_and_element_type(string_or_bytes_range):
	index_map = string_or_bytes_range.map
	
	assert isinstance(index_map, IndexMap)
	assert string_or_bytes_range.element_type is index_map.element_type
