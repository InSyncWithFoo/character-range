'''
Most test cases are dynamically generated.
(Perfect Heisenbug environment, I know.)
If edge cases are found during runs, they are
manually added to the list of parameter sets.
'''

from collections.abc import Callable, Iterator
from random import choices, randint
from typing import overload

from typing_extensions import Literal

from character_range import CharacterInterval
from character_range.character_and_byte_map import ByteInterval, ByteMap, CharacterMap


def make_interval_from_endpoints(
	start: int, end: int,
	interval_type: Literal['character', 'byte'] = 'character'
) -> CharacterInterval | ByteInterval:
	if interval_type == 'character':
		return CharacterInterval(chr(start), chr(end))
	
	return ByteInterval(
		start.to_bytes(1, 'big'),
		end.to_bytes(1, 'big')
	)


@overload
def make_map(
	intervals: list[CharacterInterval],
	lookup_char: Callable[[str], int] | None = None,
	lookup_index: Callable[[int], str] | None = None
) -> CharacterMap:
	...


@overload
def make_map(
	intervals: list[ByteInterval],
	lookup_char: Callable[[bytes], int] | None = None,
	lookup_index: Callable[[int], bytes] | None = None
) -> ByteMap:
	...


def make_map(
	intervals: list[CharacterInterval] | list[ByteInterval],
	lookup_char: Callable[[str], int] | Callable[[bytes], int] | None = None,
	lookup_index: Callable[[int], str] | Callable[[int], bytes] | None = None
) -> CharacterMap | ByteMap:
	element_type = intervals[0].element_type
	
	if issubclass(element_type, str):
		map_class = CharacterMap
	else:
		map_class = ByteMap
	
	return map_class(
		intervals = intervals,
		lookup_char = lookup_char,
		lookup_index = lookup_index
	)


def generate_random_starts_and_ends(
	interval_type: Literal['character', 'byte'],
	amount: int = 10, *,
	limits: tuple[int, int] = (0, 0x10FFFF)
) -> Iterator[tuple[int, int]]:
	if interval_type == 'byte':
		limits = (0, 255)
	
	lower_limit, upper_limit = limits
	allowed_range = range(lower_limit, upper_limit + 1)
	
	for _ in range(amount):
		yield tuple(sorted(choices(allowed_range, k = 2)))


def generate_random_intervals(
	interval_type: Literal['character', 'byte'],
	amount: int = 10, *,
	limits: tuple[int, int] = (0, 0x10FFFF)
) -> Iterator[CharacterInterval] | Iterator[ByteInterval]:
	if interval_type == 'byte':
		limits = (0, 0xFF)
	
	starts_and_ends = generate_random_starts_and_ends(
		interval_type = interval_type,
		amount = amount,
		limits = limits
	)
	
	for start, end in starts_and_ends:
		yield make_interval_from_endpoints(start, end, interval_type)


def generate_non_overlapping_intervals(
	interval_type: Literal['character', 'byte'] = 'character', /
) -> Iterator[CharacterInterval] | Iterator[ByteInterval]:
	current = 0
	
	if interval_type == 'byte':
		upper_limit = 0xFF
		span = 10
		skip = 5
	else:
		upper_limit = 0x10FFFF
		span = 20000
		skip = 10000
	
	while current < upper_limit:
		end = randint(current, current + span)
		
		try:
			interval = \
				make_interval_from_endpoints(current, end, interval_type)
		except (ValueError, OverflowError):
			break
		
		yield interval
		
		current = randint(end + 1, end + skip)
