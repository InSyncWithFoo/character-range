character_range.character_and_byte_map
======================================


.. automodule:: character_range.character_and_byte_map
   :members:
   :undoc-members:
   :exclude-members:
      Interval, CharacterInterval, ByteInterval,
      IndexMap, CharacterMap, ByteMap
   :show-inheritance:


   .. autoclass:: Interval

      .. rubric:: Attributes

      .. autoattribute:: start
      .. autoattribute:: end

      The endpoints of the interval.
      Subclasses are expected to take these two as argument
      to their ``__new__`` or ``__init__``.

      .. rubric:: Magic methods

      .. automethod:: __hash__
      .. automethod:: __iter__
      .. automethod:: __getitem__
      .. automethod:: __add__
      .. automethod:: __len__
      .. automethod:: __contains__
      .. automethod:: __str__
      .. automethod:: __eq__
      .. automethod:: __and__

      .. rubric:: Properties

      .. autoproperty:: element_type

      .. rubric:: Methods

      .. automethod:: to_codepoint_range
      .. automethod:: intersects


   .. autoclass:: CharacterInterval


   .. autoclass:: ByteInterval


   .. autoclass:: IndexMap

      .. rubric:: Methods

      .. automethod:: __hash__
      .. automethod:: __len__
      .. automethod:: __getitem__
      .. automethod:: __contains__

      .. rubric:: Properties

      .. autoproperty:: intervals
      .. autoproperty:: element_type


   .. autoclass:: CharacterMap
      :members:
      :undoc-members:


   .. autoclass:: ByteMap
      :members:
      :undoc-members:
