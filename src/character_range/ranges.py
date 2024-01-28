'''
The highest-level features of the package, implemented as
:class:`_Range`, :class:`StringRange` and :class:`BytesRange`.
'''

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from functools import total_ordering
from typing import Generic, TYPE_CHECKING, TypeVar

from typing_extensions import override, Self


if TYPE_CHECKING:
	from .maps import IndexMap

_StrOrBytes = TypeVar('_StrOrBytes', str, bytes)


def _split(value: _StrOrBytes) -> list[_StrOrBytes]:
	if isinstance(value, str):
		return list(value)
	
	return [
		byte_as_int.to_bytes(1, 'big')
		for byte_as_int in value
	]


class InvalidEndpoints(ValueError):
	'''
	Raised when the endpoints given to :class:`_Range` is either:
	
	* Empty, or
	* At least one character is not in the corresponding map.
	'''
	
	def __init__(self, *endpoints: str | bytes):
		super().__init__(', '.join(repr(endpoint) for endpoint in endpoints))


class InvalidRangeDirection(ValueError):
	'''
	Raised when ``start`` is longer than ``end`` or
	they have the same length but ``start`` is
	lexicographically "less than" end.
	'''
	
	def __init__(self, start: object, end: object) -> None:
		super().__init__(f'Start is greater than end ({start!r} > {end!r})')


@total_ordering
class _IncrementableIndexCollection:
	'''
	A collection of indices of a :class:`IndexMap`
	that can be incremented one by one.
	
	:meth:`_IncrementableIndexCollection.increment`
	works in an index-wise manner::
	
		>>> c = _IncrementableIndexCollection([1], 2)
		>>> c.increment()
		_IncrementableIndexCollection([0, 0], base = 2)
	'''
	
	__slots__ = ('_inverted_indices', '_base')
	
	_inverted_indices: list[int]
	_base: int
	
	def __init__(self, indices: Iterable[int], /, base: int) -> None:
		self._inverted_indices = list(indices)[::-1]
		self._base = base
	
	def __repr__(self) -> str:
		indices, base = self._indices, self._base
		
		return f'{self.__class__.__name__}({indices!r}, {base = !r})'
	
	def __index__(self) -> int:
		'''
		The integeral value computed by interpreting
		the indices as the digits of a base-*n* integer.
		'''
		
		total = 0
		
		for order_of_magnitude, index in enumerate(self._inverted_indices):
			total += index * self._base ** order_of_magnitude
		
		return total
	
	def __len__(self) -> int:
		'''
		The number of indices the collection currently holds.
		'''
		
		return len(self._inverted_indices)
	
	def __iter__(self) -> Iterator[int]:
		'''
		Lazily yield the elements this collection currently holds.
		'''
		
		yield from reversed(self._inverted_indices)
	
	def __lt__(self, other: Self) -> bool:
		'''
		Whether ``other``'s length is greater than ``self``'s
		or the lengths are equals but the integral value of
		``other`` is greater than that of ``self``.
		'''
		
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		if len(self) < len(other):
			return True
		
		return len(self) == len(other) and self._indices < other._indices
	
	def __eq__(self, other: object) -> bool:
		'''
		Whether two collections have the same base and elements.
		'''
		
		if not isinstance(other, self.__class__):
			return NotImplemented
		
		return self._base == other._base and self._indices == other._indices
	
	@property
	def _indices(self) -> tuple[int, ...]:
		'''
		The current indices of the collection.
		'''
		
		return tuple(self)
	
	@property
	def base(self) -> int:
		'''
		The maximum value of an index, plus 1.
		'''
		
		return self._base
	
	def increment(self) -> Self:
		'''
		Add 1 to the last index. If the new value is
		equals to ``base``, that index will become 0
		and the process continues at the next index.
		If the last index is reached, a new index (0)
		is added to the list.
		
		This is equivalent to C/C++'s pre-increment
		operator, in that it returns the original value
		after modification.
		
		Examples::
		
			[0, 0] -> [0, 1]
			[0, 1] -> [1, 0]
			[1, 1] -> [0, 0, 0]
		'''
		
		for order_of_magnitude in range(len(self._inverted_indices)):
			self._inverted_indices[order_of_magnitude] += 1
			
			if self._inverted_indices[order_of_magnitude] < self._base:
				return self
			
			self._inverted_indices[order_of_magnitude] = 0
		
		self._inverted_indices.append(0)
		
		return self


class _Range(Generic[_StrOrBytes], ABC):
	'''
	Represents a range between two
	string or bytes object endpoints.
	
	A range of this type is always a closed interval:
	both endpoints are inclusive. This goes in line
	with how regex character ranges work, even though
	those only ever support single characters::
	
		>>> list(StringRange('a', 'c', CharacterMap.ASCII_LOWERCASE))
		['a', 'b', 'c']
		>>> list(StringRange('aa', 'ac', CharacterMap.ASCII_LOWERCASE))
		['aa', 'ab', 'ac']
	
	For :class:`BytesRange`, each byte of the yielded
	:class:`bytes` objects will have the corresponding
	integral values ranging from 0 through 0xFF::
	
		>>> list(BytesRange(b'0xFE', b'0x81', ByteMap.ASCII))
		[b'0xFE', b'0xFF', b'0x80', b'0x81']
	
	Also note that the next value after
	``[base - 1]`` is ``[0, 0]``, not ``[1, 0]``::
	
		>>> list(StringRange('0', '19', CharacterMap.ASCII_DIGITS))
		[
		  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
		  '00', '01', '02', '03', '04', '05', '06', '07', '08', '09',
		  '10', '11', '12', '13', '14', '15', '16', '17', '18', '19'
		]
	
	See also :class:`_IncrementableIndexCollection`.
	'''
	
	__slots__ = ('_start', '_end', '_map')
	
	_start: _StrOrBytes
	_end: _StrOrBytes
	_map: IndexMap[_StrOrBytes]
	
	def __init__(
		self, start: _StrOrBytes, end: _StrOrBytes, /,
		index_map: IndexMap[_StrOrBytes]
	) -> None:
		self._start = start
		self._end = end
		self._map = index_map
		
		start_is_valid = self._is_valid_endpoint(start)
		end_is_valid = self._is_valid_endpoint(end)
		
		if not start_is_valid or not end_is_valid:
			raise InvalidEndpoints(start, end)
		
		if len(start) > len(end) or len(start) == len(end) and start > end:
			raise InvalidRangeDirection(start, end)
	
	def __repr__(self) -> str:
		return f'{self.__class__.__name__}({self._start!r}, {self._end!r})'
	
	def __iter__(self) -> Iterator[_StrOrBytes]:
		'''
		Lazily yield the elements.
		'''
		
		current = self._make_collection(self._start)
		end = self._make_collection(self._end)
		
		# https://github.com/python/mypy/issues/16711
		while current <= end:  # type: ignore
			yield self._make_element(current)
			current.increment()
	
	def __len__(self) -> int:
		'''
		The number of elements the range would yield,
		calculated mathematically.
		'''
		
		# Realistic example:
		# start = 'y'; end = 'aaac'
		# base = len('a'-'z') = 26
		#
		# len = (
		#     (len('a'-'z') + len('aa'-'zz') + len('aaa'-'zzz')) +
		#     len('aaaa'-'aaac') -
		#     (len('a'-'y') - len('y'-'y')
		# )
		# len = (base ** 1 + base ** 2 + base ** 3) + 3 - (25 - 1)
		# len = (26 ** 1 + 26 ** 2 + 26 ** 3) + 3 - 24
		
		start, end = self._start, self._end
		base = len(self._map)
		
		from_len_start_up_to_len_end: int = sum(
			base ** width
			for width in range(len(start), len(end))
		)
		
		from_len_start_through_start = int(self._make_collection(start))
		from_len_end_through_end = int(self._make_collection(end))
		
		result = from_len_start_up_to_len_end
		result += from_len_end_through_end
		result -= from_len_start_through_start
		result += 1
		
		return result
	
	@property
	def _base(self) -> int:
		return len(self._map)
	
	@property
	def start(self) -> _StrOrBytes:
		'''
		The starting endpoint of the range.
		'''
		
		return self._start
	
	@property
	def end(self) -> _StrOrBytes:
		'''
		The ending endpoint of the range.
		'''
		
		return self._end
	
	@property
	def map(self) -> IndexMap[_StrOrBytes]:
		'''
		The map to look up the available characters or bytes.
		'''
		
		return self._map
	
	@property
	def element_type(self) -> type[_StrOrBytes]:
		'''
		The element type of :meth:`map`.
		
		See :meth:`IndexMap.element_type`.
		'''
		
		return self._map.element_type
	
	@abstractmethod
	def _make_element(
		self, indices: _IncrementableIndexCollection, /
	) -> _StrOrBytes:
		raise NotImplementedError
	
	def _is_valid_endpoint(self, value: _StrOrBytes) -> bool:
		return (
			len(value) > 0 and
			all(char in self._map for char in _split(value))
		)
	
	def _make_collection(
		self, value: _StrOrBytes, /
	) -> _IncrementableIndexCollection:
		indices = (self._map[char] for char in _split(value))
		
		return _IncrementableIndexCollection(indices, len(self._map))


class StringRange(_Range[str]):
	
	@override
	def _make_element(self, indices: _IncrementableIndexCollection, /) -> str:
		return ''.join(self._map[index] for index in indices)


class BytesRange(_Range[bytes]):
	
	@override
	def _make_element(self, indices: _IncrementableIndexCollection, /) -> bytes:
		return b''.join(self._map[index] for index in indices)
