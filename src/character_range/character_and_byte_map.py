'''
Implementation of:

* :class:`Interval`: :class:`CharacterInterval`, :class:`ByteInterval`
* :class:`IndexMap`: :class:`CharacterMap`, :class:`ByteMap`
'''

from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from dataclasses import astuple, dataclass
from functools import cache, partial
from itertools import chain
from typing import (
	Any,
	cast,
	ClassVar,
	Generic,
	overload,
	TYPE_CHECKING,
	TypeGuard,
	TypeVar
)

from typing_extensions import Self


_T = TypeVar('_T')
_Char = TypeVar('_Char', str, bytes)
_Index = int

_LookupChar = Callable[[_Char], _Index]
_LookupIndex = Callable[[_Index], _Char]


def _ascii_repr(char: str | bytes) -> str:
	if isinstance(char, str):
		char_is_ascii_printable = ' ' <= char <= '~'
	elif isinstance(char, bytes):
		char_is_ascii_printable = b' ' <= char <= b'~'
	else:
		raise RuntimeError
	
	if char in ('\\', b'\\'):
		return r'\\'
	
	if char_is_ascii_printable:
		return char.decode() if isinstance(char, bytes) else char
	
	codepoint = ord(char)
	
	if codepoint <= 0xFF:
		return fr'\x{codepoint:02X}'
	
	if codepoint <= 0xFFFF:
		return fr'\u{codepoint:04X}'
	
	return fr'\U{codepoint:08X}'


def _is_char_of_type(
	value: str | bytes, expected_type: type[_Char], /
) -> TypeGuard[_Char]:
	return isinstance(value, expected_type) and len(value) == 1


class NoIntervals(ValueError):
	'''
	Raised when no intervals are passed
	to the map constructor.
	'''
	
	pass


class OverlappingIntervals(ValueError):
	'''
	Raised when there are at least two overlapping intervals
	in the list of intervals passed to the map constructor.
	'''
	
	def __init__(self) -> None:
		super().__init__('Intervals must not overlap')


class ConfigurationConflict(ValueError):
	'''
	Raised when the map constructor is passed:
	
	* A list of intervals whose elements don't have the same type.
	* Only one lookup function but not the other.
	'''
	
	pass


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


class InvalidIndex(LookupError):
	'''
	Raised when the index returned
	by a ``lookup_char`` function
	is not a valid index.
	'''
	
	def __init__(self, length: int, actual_index: object) -> None:
		super().__init__(
			f'Expected lookup_char to return an integer '
			f'in the interval [0, {length}], got {actual_index!r}'
		)


class InvalidChar(LookupError):
	'''
	Raised when the character returned
	by a ``lookup_index`` function
	is not of the type expected by the map.
	'''
	
	def __init__(
		self,
		actual_char: object,
		expected_type: type[str] | type[bytes]
	) -> None:
		if issubclass(expected_type, str):
			expected_type_name = 'string'
		else:
			expected_type_name = 'bytes object'
		
		super().__init__(
			f'Expected lookup_index to return '
			f'a {expected_type_name}, got {actual_char!r}'
		)


class Interval(Generic[_Char], ABC):
	'''
	An interval (both ends inclusive) of characters,
	represented using either :class:`str` or :class:`bytes`.
	
	For a :class:`CharacterInterval`, the codepoint of
	an endpoint must not be negative or greater than
	``0x10FFFF``. Similarly, for a :class:`ByteInterval`,
	the integral value of an endpoint must be in
	the interval ``[0, 255]``.
	'''
	
	start: _Char
	end: _Char
	
	# PyCharm can't infer that an immutable dataclass
	# already has __hash__ defined and will therefore
	# raise a warning if this is an @abstractmethod.
	# However, it outright rejects unsafe_hash = True
	# if __hash__ is also defined, regardless of the
	# TYPE_CHECKING guard.
	
	def __hash__(self) -> int:
		raise RuntimeError('Subclasses must implement __hash__')
	
	@abstractmethod
	def __iter__(self) -> Iterator[_Char]:
		'''
		Lazily yield each character or byte.
		'''
		
		raise NotImplementedError
	
	@abstractmethod
	def __getitem__(self, item: int) -> _Char:
		'''
		``O(1)`` indexing of character or byte.
		'''
		
		raise NotImplementedError
	
	@abstractmethod
	def __add__(self, other: Self) -> IndexMap[_Char]:
		'''
		Create a new :class:`IndexMap` with both
		``self`` and ``other`` as ``intervals``.
		'''
		
		raise NotImplementedError
	
	def __len__(self) -> int:
		'''
		The length of the interval, equivalent to
		``codepoint(start) - codepoint(end) + 1``.
		'''
		
		return len(self.to_codepoint_range())
	
	def __contains__(self, item: Any) -> bool:
		'''
		Assert that ``item``'s codepoint is
		greater than or equals to that of ``start``
		and less than or equals to that of ``end``.
		'''
		
		if not isinstance(item, self.start.__class__) or len(item) != 1:
			return False
		
		return self.start <= item <= self.end
	
	def __repr__(self) -> str:
		return f'{self.__class__.__name__}({self})'
	
	def __str__(self) -> str:
		if len(self) == 1:
			return _ascii_repr(self.start)
		
		return f'{_ascii_repr(self.start)}-{_ascii_repr(self.end)}'
	
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
		See :meth:`Interval.intersects`.
		'''
		
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		earlier_end = min(self.end, other.end)
		later_start = max(self.start, other.start)
		
		return later_start <= earlier_end
	
	@property
	@abstractmethod
	def element_type(self) -> type[_Char]:
		'''
		A class-based property that returns
		the type of the interval's elements.
		'''
		
		raise NotImplementedError
	
	def _validate(self, *, exception_type: type[ValueError]) -> None:
		if not _is_char_of_type(self.start, self.element_type):
			raise exception_type(self.start)
		
		if not _is_char_of_type(self.end, self.element_type):
			raise exception_type(self.end)
		
		if self.start > self.end:
			raise InvalidIntervalDirection(self.start, self.end)
	
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


@dataclass(
	eq = False, frozen = True, repr = False,
	slots = True, unsafe_hash = True
)
class CharacterInterval(Interval[str]):
	start: str
	end: str
	
	def __post_init__(self) -> None:
		self._validate(exception_type = NotACharacter)
	
	def __iter__(self) -> Iterator[str]:
		for codepoint in self.to_codepoint_range():
			yield chr(codepoint)
	
	def __getitem__(self, item: int) -> str:
		if not 0 <= item < len(self):
			raise IndexError('Index out of range')
		
		return chr(ord(self.start) + item)
	
	def __add__(self, other: Self) -> CharacterMap:
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		return CharacterMap([self, other])
	
	@property
	def element_type(self) -> type[str]:
		return str


@dataclass(
	eq = False, frozen = True, repr = False,
	slots = True, unsafe_hash = True
)
class ByteInterval(Interval[bytes]):
	start: bytes
	end: bytes
	
	def __post_init__(self) -> None:
		self._validate(exception_type = NotAByte)
	
	def __iter__(self) -> Iterator[bytes]:
		for bytes_value in self.to_codepoint_range():
			yield bytes_value.to_bytes(1, 'big')
	
	def __getitem__(self, item: int) -> bytes:
		if not isinstance(item, int):
			raise TypeError(f'Expected a non-negative integer, got {item}')
		
		if not 0 <= item < len(self):
			raise IndexError('Index out of range')
		
		return (ord(self.start) + item).to_bytes(1, 'big')
	
	def __add__(self, other: Self) -> ByteMap:
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		return ByteMap([self, other])
	
	@property
	def element_type(self) -> type[bytes]:
		return bytes


@dataclass(frozen = True, slots = True)
class _Searchers(Generic[_Char]):
	lookup_char: _LookupChar[_Char] | None
	lookup_index: _LookupIndex[_Char] | None
	
	@property
	def both_given(self) -> bool:
		'''
		Whether both functions are not ``None``.
		'''
		
		return self.lookup_char is not None and self.lookup_index is not None
	
	@property
	def both_omitted(self) -> bool:
		'''
		Whether both functions are ``None``.
		'''
		
		return self.lookup_char is None and self.lookup_index is None
	
	@property
	def only_one_given(self) -> bool:
		'''
		Whether only one of the functions is ``None``.
		'''
		
		return not self.both_given and not self.both_omitted


class _RunCallbackAfterInitialization(type):
	'''
	:class:`_HasPrebuiltMembers`'s metaclass (a.k.a. metametaclass).
	Runs a callback defined at the instance's level.
	'''
	
	_callback_method_name: str
	
	def __call__(cls, *args: object, **kwargs: object) -> Any:
		class_with_prebuilt_members = super().__call__(*args, **kwargs)
		
		callback = getattr(cls, cls._callback_method_name)
		callback(class_with_prebuilt_members)
		
		return class_with_prebuilt_members


# This cannot be generic due to
# https://github.com/python/mypy/issues/11672
class _HasPrebuiltMembers(
	ABCMeta,
	metaclass = _RunCallbackAfterInitialization
):
	'''
	:class:`CharacterMap` and :class:`ByteMap`'s metaclass.
	'''
	
	_callback_method_name: ClassVar[str] = '_instantiate_members'
	
	# When the `cls` (`self`) argument is typed as 'type[_T]',
	# mypy refuses to understand that it also has the '_member_names'
	# attribute, regardless of assertions and castings.
	# The way to circumvent this is to use 'getattr()',
	# as demonstrated below in '__getitem__' and 'members'.
	_member_names: list[str]
	
	def __new__(
		mcs,
		name: str,
		bases: tuple[type, ...],
		namespace: dict[str, Any],
		**kwargs: Any
	) -> _HasPrebuiltMembers:
		new_class = super().__new__(mcs, name, bases, namespace, **kwargs)
		
		if ABC in bases:
			return new_class
		
		new_class._member_names = [
			name for name, value in new_class.__dict__.items()
			if not name.startswith('_') and not callable(value)
		]
		
		return new_class
	
	def __getitem__(cls: type[_T], item: str) -> _T:
		member_names: list[str] = getattr(cls, '_member_names')
		
		if item not in member_names:
			raise LookupError(f'No such member: {item!r}')
		
		return cast(_T, getattr(cls, item))
	
	@property
	def members(cls: type[_T]) -> tuple[_T, ...]:
		'''
		Returns a tuple of pre-built members of the class.
		'''
		
		member_names: list[str] = getattr(cls, '_member_names')
		
		return tuple(getattr(cls, name) for name in member_names)
	
	def _instantiate_members(cls) -> None:
		for member_name in cls._member_names:
			value = getattr(cls, member_name)
			
			if isinstance(value, tuple):
				setattr(cls, member_name, cls(*value))
			else:
				setattr(cls, member_name, cls(value))


class IndexMap(Generic[_Char], ABC):
	'''
	A two-way mapping between character or byte
	to its corresponding index.
	'''
	
	__slots__ = (
		'_intervals', '_char_to_index',
		'_searchers', '_index_to_char',
		'_maps_populated', '_element_type',
		'_not_a_char_exception'
	)
	
	_intervals: tuple[Interval[_Char], ...]
	_char_to_index: dict[_Char, _Index]
	_index_to_char: dict[_Index, _Char]
	_searchers: _Searchers[_Char]
	_element_type: type[_Char]
	_maps_populated: bool
	_not_a_char_exception: type[NotACharacter] | type[NotAByte]
	
	def __init__(
		self,
		intervals: Iterable[Interval[_Char]],
		lookup_char: _LookupChar[_Char] | None = None,
		lookup_index: _LookupIndex[_Char] | None = None
	) -> None:
		r'''
		Construct a new map from a number of intervals.
		The underlying character-to-index and
		index-to-character maps will not be populated if
		lookup functions are given.
		
		Lookup functions are expected to be the optimized
		versions of the naive, brute-force lookup algorithm.
		This relationship is similar to that of
		``__method__``\ s and built-ins; for example,
		while ``__contains__`` is automatically
		implemented when a class defines both ``__len__``
		and ``__getitem__``, a ``__contains__`` may still
		be needed if manual iterations are too
		unperformant, unnecessary or unwanted.
		
		Lookup functions must raise either
		:class:`LookupError` or :class:`ValueError`
		if the index or character cannot be found.
		If the index returned by ``lookup_char`` is
		not in the interval ``[0, len(self) - 1]``,
		a :class:`ValueError` is raised.
		
		:raise ConfigurationConflict: \
			If only one lookup function is given.
		:raise NoIntervals: \
			If no intervals are given.
		'''
		
		self._intervals = tuple(intervals)
		self._searchers = _Searchers(lookup_char, lookup_index)
		
		self._char_to_index = {}
		self._index_to_char = {}
		
		if self._searchers.only_one_given:
			raise ConfigurationConflict(
				'The two lookup functions must be either '
				'both given or both omitted'
			)
		
		if not self._intervals:
			raise NoIntervals('At least one interval expected')
		
		self._intervals_must_have_same_type()
		self._element_type = self._intervals[0].element_type
		
		if issubclass(self._element_type, str):
			self._not_a_char_exception = NotACharacter
		elif issubclass(self._element_type, bytes):
			self._not_a_char_exception = NotAByte
		else:
			raise RuntimeError
		
		if self._searchers.both_given:
			self._intervals_must_not_overlap()
			self._maps_populated = False
			return
		
		self._populate_maps()
		self._maps_populated = True
	
	def __hash__(self) -> int:
		return hash(self._intervals)
	
	@cache
	def __len__(self) -> int:
		if self._maps_populated:
			return len(self._char_to_index)
		
		return sum(len(interval) for interval in self._intervals)
	
	@cache
	def __repr__(self) -> str:
		joined_ranges = ''.join(str(interval) for interval in self._intervals)
		
		return f'{self.__class__.__name__}({joined_ranges})'
	
	@overload
	def __getitem__(self, item: _Char) -> _Index:
		...
	
	@overload
	def __getitem__(self, item: _Index) -> _Char:
		...
	
	def __getitem__(self, item: _Char | _Index) -> _Index | _Char:
		'''
		Either look for the character/index in the underlying maps,
		or delegate that task to the look-up functions given.
		
		Results are cached.
		
		:raise ValueError: \
			If ``item`` is neither a character/byte nor an index.
		:raise IndexError: \
			If ``lookup_char``
		'''
		
		if isinstance(item, int):
			return self._get_char_given_index(item)
		
		if isinstance(item, self._element_type):
			return self._get_index_given_char(item)
		
		raise TypeError(f'Expected a character or an index, got {item!r}')
	
	def __contains__(self, item: object) -> bool:
		if not isinstance(item, self._element_type | int):
			return False
		
		if isinstance(item, int):
			return 0 <= item < len(self)
		
		try:
			# This is necessary for PyCharm,
			# deemed redundant by mypy,
			# and makes pyright think that 'item' is of type 'object'.
			item = cast(_Char, item)  # type: ignore
			
			_ = self._get_index_given_char(item)
		except (LookupError, ValueError):
			return False
		else:
			return True
	
	def __eq__(self, other: object) -> bool:
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		return self._intervals == other._intervals
	
	# Needed for testing and type hint convenience
	def __add__(self, other: Self | IndexMap[_Char] | Interval[_Char]) -> Self:
		if not isinstance(other, IndexMap | Interval):
			return NotImplemented
		
		if other.element_type is not self.element_type:
			raise ConfigurationConflict('Different element types')
		
		lookup_char, lookup_index = astuple(self._searchers)
		
		if isinstance(other, Interval):
			return self.__class__(
				self._intervals + tuple([other]),
				lookup_char = lookup_char,
				lookup_index = lookup_index
			)
		
		if self._searchers != other._searchers:
			raise ConfigurationConflict(
				'Maps having different lookup functions '
				'cannot be combined'
			)
		
		return self.__class__(
			self._intervals + other._intervals,
			lookup_char = lookup_char,
			lookup_index = lookup_index
		)
	
	@property
	def intervals(self) -> tuple[Interval[_Char], ...]:
		'''
		The intervals that make up the map.
		'''
		
		return self._intervals
	
	@property
	def element_type(self) -> type[_Char]:
		'''
		The type of the map's elements.
		'''
		
		return self._element_type
	
	def _intervals_must_have_same_type(self) -> None:
		interval_types = {type(interval) for interval in self._intervals}
		
		if len(interval_types) > 1:
			raise ConfigurationConflict('Intervals must be of same types')
	
	def _intervals_must_not_overlap(self) -> None:
		seen: list[Interval[_Char]] = []
		
		for current_interval in self._intervals:
			overlapped = any(
				current_interval.intersects(seen_interval)
				for seen_interval in seen
			)
			
			if overlapped:
				raise OverlappingIntervals
			
			seen.append(current_interval)
	
	def _populate_maps(self) -> None:
		chained_intervals = chain.from_iterable(self._intervals)
		
		for index, char in enumerate(chained_intervals):
			if char in self._char_to_index:
				raise OverlappingIntervals
			
			self._char_to_index[char] = index
			self._index_to_char[index] = char
	
	def _get_char_given_index(self, index: _Index, /) -> _Char:
		if index not in self:
			raise IndexError(f'Index {index} is out of range')
		
		if index in self._index_to_char:
			return self._index_to_char[index]
		
		lookup_index = self._searchers.lookup_index
		assert lookup_index is not None
		
		result = lookup_index(index)
		
		if not _is_char_of_type(result, self._element_type):
			raise InvalidChar(result, self._element_type)
		
		self._index_to_char[index] = result
		return self._index_to_char[index]
	
	def _get_index_given_char(self, char: _Char, /) -> _Index:
		if not _is_char_of_type(char, self._element_type):
			raise self._not_a_char_exception(char)
		
		if char in self._char_to_index:
			return self._char_to_index[char]
		
		lookup_char = self._searchers.lookup_char
		
		if lookup_char is None:
			raise LookupError(f'Char {char!r} is not in the map')
		
		result = lookup_char(char)
		
		if not isinstance(result, int) or result not in self:
			raise InvalidIndex(len(self), result)
		
		self._char_to_index[char] = result
		return self._char_to_index[char]


def _ascii_index_from_char_or_byte(char_or_byte: str | bytes) -> int:
	codepoint = ord(char_or_byte)
	
	if not 0 <= codepoint <= 0xFF:
		raise ValueError('Not an ASCII character or byte')
	
	return codepoint


@overload
def _ascii_char_or_byte_from_index(constructor: type[str], index: int) -> str:
	...


@overload
def _ascii_char_or_byte_from_index(
	constructor: type[bytes],
	index: int
) -> bytes:
	...


def _ascii_char_or_byte_from_index(
	constructor: type[str] | type[bytes],
	index: int
) -> str | bytes:
	if issubclass(constructor, str):
		return constructor(chr(index))
	
	if issubclass(constructor, bytes):
		# \x80 and higher would be converted
		# to two bytes with .encode() alone.
		return constructor(index.to_bytes(1, 'big'))
	
	raise RuntimeError


_ascii_char_from_index = cast(
	Callable[[int], str],
	partial(_ascii_char_or_byte_from_index, str)
)
_ascii_byte_from_index = cast(
	Callable[[int], bytes],
	partial(_ascii_char_or_byte_from_index, bytes)
)

if TYPE_CHECKING:
	class CharacterMap(IndexMap[str], metaclass = _HasPrebuiltMembers):
		# At runtime, this is a read-only class-level property.
		members: ClassVar[tuple[CharacterMap, ...]]
		
		ASCII_LOWERCASE: ClassVar[CharacterMap]
		ASCII_UPPERCASE: ClassVar[CharacterMap]
		ASCII_LETTERS: ClassVar[CharacterMap]
		
		ASCII_DIGITS: ClassVar[CharacterMap]
		
		LOWERCASE_HEX_DIGITS: ClassVar[CharacterMap]
		UPPERCASE_HEX_DIGITS: ClassVar[CharacterMap]
		
		LOWERCASE_BASE_36: ClassVar[CharacterMap]
		UPPERCASE_BASE_36: ClassVar[CharacterMap]
		
		ASCII: ClassVar[CharacterMap]
		NON_ASCII: ClassVar[CharacterMap]
		UNICODE: ClassVar[CharacterMap]
		
		# At runtime, this functionality is provided
		# using the metaclass's __getitem__.
		def __class_getitem__(cls, item: str) -> CharacterMap:
			...
	
	
	class ByteMap(IndexMap[bytes], metaclass = _HasPrebuiltMembers):
		# At runtime, this is a read-only class-level property.
		members: ClassVar[tuple[ByteMap, ...]]
		
		ASCII_LOWERCASE: ClassVar[ByteMap]
		ASCII_UPPERCASE: ClassVar[ByteMap]
		ASCII_LETTERS: ClassVar[ByteMap]
		
		ASCII_DIGITS: ClassVar[ByteMap]
		
		LOWERCASE_HEX_DIGITS: ClassVar[ByteMap]
		UPPERCASE_HEX_DIGITS: ClassVar[ByteMap]
		
		LOWERCASE_BASE_36: ClassVar[ByteMap]
		UPPERCASE_BASE_36: ClassVar[ByteMap]
		
		ASCII: ClassVar[ByteMap]
		
		# At runtime, this functionality is provided
		# using the metaclass's __getitem__.
		def __class_getitem__(cls, item: str) -> ByteMap:
			...

else:
	class CharacterMap(IndexMap[str], metaclass = _HasPrebuiltMembers):
		ASCII_LOWERCASE = [CharacterInterval('a', 'z')]
		ASCII_UPPERCASE = [CharacterInterval('A', 'Z')]
		ASCII_LETTERS = ASCII_LOWERCASE + ASCII_UPPERCASE
		
		ASCII_DIGITS = [CharacterInterval('0', '9')]
		
		LOWERCASE_HEX_DIGITS = ASCII_DIGITS + [CharacterInterval('a', 'f')]
		UPPERCASE_HEX_DIGITS = ASCII_DIGITS + [CharacterInterval('A', 'F')]
		
		LOWERCASE_BASE_36 = ASCII_DIGITS + ASCII_LOWERCASE
		UPPERCASE_BASE_36 = ASCII_DIGITS + ASCII_UPPERCASE
		
		ASCII = (
			[CharacterInterval('\x00', '\xFF')],
			_ascii_index_from_char_or_byte,
			_ascii_char_from_index
		)
		NON_ASCII = (
			[CharacterInterval('\u0100', '\U0010FFFF')],
			lambda char: ord(char) - 0x100,
			lambda index: chr(index + 0x100)
		)
		UNICODE = ([CharacterInterval('\x00', '\U0010FFFF')], ord, chr)
	
	
	class ByteMap(IndexMap[bytes], metaclass = _HasPrebuiltMembers):
		ASCII_LOWERCASE = [ByteInterval(b'a', b'z')]
		ASCII_UPPERCASE = [ByteInterval(b'A', b'Z')]
		ASCII_LETTERS = ASCII_LOWERCASE + ASCII_UPPERCASE
		
		ASCII_DIGITS = [ByteInterval(b'0', b'9')]
		
		LOWERCASE_HEX_DIGITS = ASCII_DIGITS + [ByteInterval(b'a', b'f')]
		UPPERCASE_HEX_DIGITS = ASCII_DIGITS + [ByteInterval(b'A', b'F')]
		
		LOWERCASE_BASE_36 = ASCII_DIGITS + ASCII_LOWERCASE
		UPPERCASE_BASE_36 = ASCII_DIGITS + ASCII_UPPERCASE
		
		ASCII = (
			[ByteInterval(b'\x00', b'\xFF')],
			_ascii_index_from_char_or_byte,
			_ascii_byte_from_index
		)
