'''
Implementation of :class:`Interval`,
:class:`CharacterInterval` and :class:`ByteInterval`.
'''

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, ClassVar, Generic, overload, SupportsIndex, TypeGuard, TypeVar

from typing_extensions import override, Self


_Char = TypeVar('_Char', str, bytes)


def _ascii_repr(char: str | bytes) -> str:
	if isinstance(char, str):
		char_is_ascii_printable = ' ' <= char <= '~'
	else:
		char_is_ascii_printable = b' ' <= char <= b'~'
	
	if char in ('\\', b'\\'):
		return r'\\'
	
	if char in ('-', b'-'):
		return r'\-'
	
	if char_is_ascii_printable:
		return char.decode() if isinstance(char, bytes) else char
	
	codepoint = ord(char)
	
	if codepoint <= 0xFF:
		return fr'\x{codepoint:02X}'
	
	if codepoint <= 0xFFFF:
		return fr'\u{codepoint:04X}'
	
	return fr'\U{codepoint:08X}'


def _is_char_of_type(
	value: object, expected_type: type[_Char], /
) -> TypeGuard[_Char]:
	return isinstance(value, expected_type) and len(value) == 1


def _is_valid_codepoint_range(
	codepoint_range: range, /,
	upper_limit: int
) -> bool:
	start, stop, step = (
		codepoint_range.start,
		codepoint_range.stop,
		codepoint_range.step
	)
	
	return 0 <= start < stop <= upper_limit and step == 1


class InvalidIntervalDirection(ValueError):
	'''
	Raised when an interval constructor is passed
	a ``start`` whose value is greater than that of ``end``.
	'''
	
	def __init__(self, start: _Char, stop: _Char) -> None:
		super().__init__(
			f'Expected stop to be greater than or equals to start, '
			f'got {start!r} > {stop!r}'
		)


class NotACharacter(ValueError):
	'''
	Raised when an object is expected to be a character
	(a :class:`str` of length 1) but it is not one.
	'''
	
	def __init__(self, actual: object) -> None:
		if isinstance(actual, str):
			value_repr = f'string of length {len(actual)}'
		else:
			value_repr = repr(actual)
		
		super().__init__(f'Expected a character, got {value_repr}')


class NotAByte(ValueError):
	'''
	Raised when an object is expected to be a byte
	(a :class:`bytes` object of length 1) but it is not one.
	'''
	
	def __init__(self, actual: object) -> None:
		if isinstance(actual, bytes):
			value_repr = f'a bytes object of length {len(actual)}'
		else:
			value_repr = repr(actual)
		
		super().__init__(f'Expected a single byte, got {value_repr!r}')


class InvalidCodepointRange(ValueError):
	'''
	Raised when a :class:`range` cannot be interpreted as
	an :class:`Interval`'s codepoint range.
	'''
	
	pass


class Interval(Generic[_Char], ABC):
	'''
	An interval (both ends inclusive) of characters,
	represented using either :class:`str` or :class:`bytes`.
	'''
	
	_not_a_char_exception: ClassVar[type[ValueError]]
	'''
	Exception raised when an object is expected
	to be a character but it is not.
	'''
	_max_value: ClassVar[int]
	'''
	The maximum integral value that can be converted to a character.
	'''
	
	__slots__ = ('_start', '_end')
	
	_start: _Char
	_end: _Char
	
	def __new__(cls, start: _Char, end: _Char) -> 'Self':
		'''
		Construct a new interval.
		
		:param start: The start of the interval, inclusive.
		:param end: The end of the interval, inclusive.
		'''
		
		instance = super().__new__(cls)
		instance._start = start
		instance._end = end
		
		not_a_char_exception = cls._not_a_char_exception
		element_type = instance.element_type
		
		if not _is_char_of_type(start, element_type):
			raise not_a_char_exception(start)
		
		if not _is_char_of_type(end, element_type):
			raise not_a_char_exception(end)
		
		if start > end:
			raise InvalidIntervalDirection(start, end)
		
		return instance
	
	def __hash__(self) -> int:
		return hash((self.element_type, self.start, self.end))
	
	def __iter__(self) -> Iterator[_Char]:
		'''
		Lazily yield each character or byte.
		'''
		
		for codepoint in self.to_codepoint_range():
			yield self._make_element(codepoint)
	
	def __reversed__(self) -> Iterator[_Char]:
		'''
		Lazily yield each character or byte in reverse order.
		'''
		
		for codepoint in reversed(self.to_codepoint_range()):
			yield self._make_element(codepoint)
	
	@overload
	def __getitem__(self, item: slice) -> Self:
		...
	
	@overload
	def __getitem__(self, item: SupportsIndex) -> _Char:
		...
	
	def __getitem__(self, item: slice | SupportsIndex) -> Self | _Char:
		'''
		``O(1)`` indexing of character or byte.
		:class:`slice` objects are also supported.
		'''
		
		if isinstance(item, SupportsIndex):
			item = int(item)
			integral_element = self.to_codepoint_range()[item]
			return self._make_element(integral_element)
		
		new_codepoint_range = self.to_codepoint_range()[item]
		
		try:
			return self.__class__.from_codepoint_range(new_codepoint_range)
		except InvalidCodepointRange as exception:
			outer_exception = InvalidCodepointRange(
				f'The interval derived from slicing self '
				f'with {item!r} is invalid'
			)
			
			raise outer_exception from exception
	
	def __len__(self) -> int:
		'''
		The length of the interval, equivalent to
		``codepoint(end) - codepoint(start) + 1``.
		'''
		
		return len(self.to_codepoint_range())
	
	def __contains__(self, item: Any) -> bool:
		'''
		Assert that ``item`` is a valid element
		and that it is lexicographically
		greater than or equals to that of ``start``
		and less than or equals to that of ``end``.
		'''
		
		if not _is_char_of_type(item, self.element_type):
			return False
		
		return self._start <= item <= self._end
	
	def __repr__(self) -> str:
		return f'{self.__class__.__name__}({self})'
	
	def __str__(self) -> str:
		r'''
		Return an ASCII representation of the range, typically
		looks like ``\x00-a``, ``\--\uFFFD`` or ``\U00100000``.
		'''
		
		if len(self) == 1:
			return _ascii_repr(self._start)
		
		return f'{_ascii_repr(self._start)}-{_ascii_repr(self._end)}'
	
	def __eq__(self, other: object) -> bool:
		'''
		Two intervals are equal if one is an instance of
		the other's class and their endpoints have the
		same integral values.
		'''
		
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		return self.to_codepoint_range() == other.to_codepoint_range()
	
	def __and__(self, other: Self) -> bool:
		'''
		See :meth:`.intersects`.
		'''
		
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		earlier_end = min(self._end, other._end)
		later_start = max(self._start, other._start)
		
		return later_start <= earlier_end
	
	@property
	def start(self) -> _Char:
		'''
		The starting endpoint of the interval.
		'''
		
		return self._start
	
	@property
	def end(self) -> _Char:
		'''
		The ending endpoint of the interval.
		'''
		
		return self._end
	
	@property
	@abstractmethod
	def element_type(self) -> type[_Char]:
		'''
		A class-based property that returns
		the type of the interval's elements.
		'''
		
		raise NotImplementedError
	
	@classmethod
	@abstractmethod
	def _make_element(cls, value: int, /) -> _Char:
		'''
		Convert an integral value to the interval's
		element type.
		
		Subclasses must raise :class:`ValueError`
		if ``value`` cannot be converted to an element.
		'''
		
		raise NotImplementedError
	
	def to_codepoint_range(self) -> range:
		'''
		Convert the interval to a native :class:`range` that
		would yield the codepoints of the elements of the interval.
		'''
		
		return range(ord(self.start), ord(self.end) + 1)
	
	def intersects(self, other: Self) -> bool:
		'''
		Whether two intervals intersect each other.
		'''
		
		return self & other
	
	@classmethod
	def from_codepoint_range(cls, codepoint_range: range, /) -> Self:
		'''
		Construct an interval from a :class:`range` of codepoints.
		
		As a technical limit, for a :class:`CharacterInterval`,
		the codepoint of an endpoint must not be negative or
		greater than ``0x10FFFF``. Similarly, for a
		:class:`ByteInterval`, the integral value of an endpoint
		must be in the interval ``[0, 255]``.
		'''
		
		upper_limit = cls._max_value + 1
		
		if not _is_valid_codepoint_range(codepoint_range, upper_limit):
			raise InvalidCodepointRange(
				f'Expected 0 <= start < stop <= {upper_limit} '
				f'and step == 1, got {codepoint_range!r}'
			)
		
		start, stop = codepoint_range.start, codepoint_range.stop
		
		start_element = cls._make_element(start)
		stop_element = cls._make_element(max(0, stop - 1))
		
		return cls(start_element, stop_element)


class CharacterInterval(Interval[str]):
	
	_not_a_char_exception = NotACharacter
	_max_value = 0x10FFFF
	'''
	The maximum integral value of a Unicode codepoint: ``0x10FFFF``.
	'''
	
	@property
	@override
	def element_type(self) -> type[str]:
		return str
	
	@classmethod
	@override
	def _make_element(cls, value: int, /) -> str:
		return chr(value)


class ByteInterval(Interval[bytes]):
	
	_not_a_char_exception = NotAByte
	_max_value = 0xFF
	'''
	The maximum integral value of a byte (16 bits): ``0xFF``.
	'''
	
	@property
	@override
	def element_type(self) -> type[bytes]:
		return bytes
	
	@classmethod
	@override
	def _make_element(cls, value: int, /) -> bytes:
		return value.to_bytes(1, 'big')
