# Character range

![Tests][1]
![Documentation Status][2]

This package does exactly what it says on the tin:
Create a string or bytes range.

```python
from character_range import (
  ByteMap, character_range, CharacterMap,
  string_range, bytes_range
)

print(list(character_range('a', 'z')))
# 'a', 'b', ..., 'y', 'z'

for element in string_range('aaa', 'aba', CharacterMap.ASCII_LOWERCASE):
  print(element)  # 'aaa', 'aab', ..., 'aay', 'aaz', 'aba'

for element in bytes_range(b'0', b'10', ByteMap.ASCII_LOWERCASE):
  print(element)  # b'0', b'1', ..., b'9', b'00', b'01', ..., b'09', b'10'
```

For more information, see [the documentation][3].

## Installation

This package is available [on PyPI][4]:

```shell
$ pip install character-range
```


## Contributing

Please see _[Contributing][5]_ for more information.


  [1]: https://github.com/InSyncWithFoo/character-range/actions/workflows/tests.yaml/badge.svg
  [2]: https://readthedocs.org/projects/character-range/badge/?version=latest
  [3]: https://character-range.readthedocs.io/
  [4]: https://pypi.org/project/character-range
  [5]: ./CONTRIBUTING.md
