character_range.interval
========================


.. automodule:: character_range.intervals
   :members:
   :undoc-members:
   :exclude-members:
      Interval, CharacterInterval, ByteInterval
   :show-inheritance:


   .. autoclass:: CharacterInterval

      .. rubric:: Class variables

      .. autoattribute:: _max_value


   .. autoclass:: ByteInterval

      .. rubric:: Class variables

      .. autoattribute:: _max_value


   .. autoclass:: Interval

      .. rubric:: Class variables

      .. autoattribute:: _max_value

      .. rubric:: Magic methods

      .. automethod:: __hash__
      .. automethod:: __iter__
      .. automethod:: __reversed__
      .. automethod:: __getitem__
      .. automethod:: __len__
      .. automethod:: __contains__
      .. automethod:: __repr__
      .. automethod:: __str__
      .. automethod:: __eq__
      .. automethod:: __and__

      .. rubric:: Properties

      .. autoproperty:: start
      .. autoproperty:: end
      .. autoproperty:: element_type

      .. rubric:: Methods

      .. automethod:: to_codepoint_range
      .. automethod:: intersects

      .. rubric:: Class methods

      .. automethod:: from_codepoint_range
