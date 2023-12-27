# Character range

![Tests][1]


This package does exactly what it says on the tin:
Create a string or bytes range.

```python
from character_range import ByteMap, character_range, CharacterMap


for element in character_range('aaa', 'aba', CharacterMap.ASCII_LOWERCASE):
    print(element)  # 'aaa', 'aab', ..., 'aay', 'aaz', 'aba'

for element in character_range(b'0', b'10', ByteMap.ASCII_LOWERCASE):
    print(element)  # b'0', b'1', ..., b'9', b'00', b'01', ..., b'09', b'10'
```

## Installation

```shell
$ pip install character-range
```


  [1]: https://github.com/InSyncWithFoo/character-range/actions/workflows/tests.yaml/badge.svg
