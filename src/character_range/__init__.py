'''
Does exactly what it says on the tin:

	>>> list(character_range('aaa', 'aba', CharacterMap.ASCII_LOWERCASE))
	['aaa', 'aab', ..., 'aay', 'aaz', 'aba']
	>>> character_range(b'0', b'10', ByteMap.ASCII_DIGITS)
	[b'0', b'1', ..., b'9', b'00', b'01', ..., b'09', b'10']

'''

from .character_and_byte_map import (
	ByteInterval, ByteMap,
	CharacterInterval, CharacterMap
)
from .string_and_bytes_range import (
	BytesRange,
	character_range,
	StringRange
)


__all__ = [
	'ByteInterval', 'ByteMap', 'BytesRange',
	'CharacterInterval', 'CharacterMap', 'StringRange',
	'character_range'
]
