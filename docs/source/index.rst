character-range v\ |version|
============================

``character-range`` does exactly what it says on the tin:
Create a string or bytes range. For more information,
see :ref:`API references <api-references>`.

.. code-block:: python

   from character_range import ByteMap, character_range, CharacterMap

   for element in character_range('aaa', 'aba', CharacterMap.ASCII_LOWERCASE):
      print(element)  # 'aaa', 'aab', ..., 'aay', 'aaz', 'aba'

   for element in character_range(b'0', b'10', ByteMap.ASCII_LOWERCASE):
      print(element)  # b'0', b'1', ..., b'9', b'00', b'01', ..., b'09', b'10'


Installation
------------

``character-range`` is available `on PyPI`_:

.. code-block:: console

   $ pip install character-range


.. _api-references:

API references
--------------

.. toctree::
   :maxdepth: 2

   Ranges <range>
   Intervals and maps <map>


.. _on PyPI: https://pypi.python.org/project/character-range
