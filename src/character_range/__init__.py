'''
This package does exactly what it says on the tin:

	>>> list(string_range('aaa', 'aba', CharacterMap.ASCII_LOWERCASE))
	['aaa', 'aab', ..., 'aay', 'aaz', 'aba']
	>>> list(bytes_range(b'0', b'10', ByteMap.ASCII_DIGITS))
	[b'0', b'1', ..., b'9', b'00', b'01', ..., b'09', b'10']

'''

from enum import IntEnum
from typing import overload

from .maps import ByteMap, CharacterMap, IndexMap
from .intervals import ByteInterval, CharacterInterval
from .ranges import BytesRange, StringRange


__all__ = [
	'ByteInterval', 'ByteMap', 'BytesRange',
	'CharacterInterval', 'CharacterMap', 'StringRange',
	'character_range', 'UnrecognizedEndpointTypes',
	'string_range', 'bytes_range'
]


# TODO: Support different range types
class _RangeType(IntEnum):  # pyright: ignore
	'''
	Given a range/interval from ``a`` to ``z``:

	+------------+----------------+----------------+
	| Range type | Contains ``a`` | Contains ``z`` |
	+============+================+================+
	| Open       |       No       |       No       |
	+------------+----------------+----------------+
	| Left-open  |       No       |      Yes       |
	+------------+----------------+----------------+
	| Right-open |      Yes       |       No       |
	+------------+----------------+----------------+
	| Closed     |      Yes       |      Yes       |
	+------------+----------------+----------------+

	These terms are taken from
	`the Wikipedia article about mathematical intervals \
	<https://en.wikipedia.org/wiki/Interval_(mathematics)>`_.
	
	A :class:`Range`/:class:`Interval` are always closed.
	However, for convenience, :func:`character_range`,
	:func:`string_range` and :func:`bytes_range` each
	will accept an optional ``range_type`` argument that
	deals with these.
	'''
	
	OPEN = 0b00
	LEFT_OPEN = 0b01
	RIGHT_OPEN = 0b10
	CLOSED = 0b11


class UnrecognizedEndpointTypes(TypeError):
	'''
	Raised when the given endpoints of a range have different types.
	'''
	
	def __init__(self, start_types: type, end_types: type):
		types = (start_types.__name__, end_types.__name__)
		
		super().__init__(f'Expected (str, str) or (bytes, bytes), got {types}')


@overload
def character_range(start: str, end: str) -> CharacterInterval:
	...


@overload
def character_range(start: bytes, end: bytes) -> ByteInterval:
	...


def character_range(
	start: str | bytes, end: str | bytes
) -> CharacterInterval | ByteInterval:
	'''
	:class:`range`-like alias for
	:class:`CharacterInterval` and :class:`ByteInterval`.
	'''
	
	if isinstance(start, str) and isinstance(end, str):
		return CharacterInterval(start, end)
	
	if isinstance(start, bytes) and isinstance(end, bytes):
		return ByteInterval(start, end)
	
	raise UnrecognizedEndpointTypes(type(start), type(end))


def string_range(
	start: str, end: str,
	index_map: IndexMap[str]
) -> StringRange:
	'''
	:class:`range`-like alias for :class:`StringRange`.
	'''
	
	return StringRange(start, end, index_map)


def bytes_range(
	start: bytes, end: bytes,
	index_map: IndexMap[bytes]
) -> BytesRange:
	'''
	:class:`range`-like alias for :class:`BytesRange`.
	'''
	
	return BytesRange(start, end, index_map)
