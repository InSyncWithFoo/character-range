# Changelog


## v0.2.0 - 2024-01-23

* Add more project files.
* Change license from Unlicense to MIT.
* Partly migrate error-prone random test generators to Hypothesis.
* `character_range` no longer returns `StringRange` or `BytesRange`.
  `string_range` and `bytes_range` are the replacements.
* Functional aliases are now placed in `__init__.py`.
* Move `Interval` classes to their own module.
  Use shorter names for modules.
* `IndexMap`'s `__len__` and `__repr__` are now manually cached.
  This also prevents memory leaks due to `self` not being garbage collected.
* Add support for Pyright.

## v0.1.0 - 2023-12-27

* Fresh out of oven!
