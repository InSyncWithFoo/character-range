character_range.ranges
======================


.. automodule:: character_range.ranges
   :members:
   :undoc-members:
   :exclude-members: StringRange, BytesRange
   :show-inheritance:


   .. autoclass:: StringRange
      :members:
      :undoc-members:
      :show-inheritance:


   .. autoclass:: BytesRange
      :members:
      :undoc-members:
      :show-inheritance:


   .. autoclass:: _Range
      :show-inheritance:

      .. rubric:: Magic methods

      .. automethod:: __iter__
      .. automethod:: __len__

      .. rubric:: Properties

      .. autoproperty:: start
      .. autoproperty:: end
      .. autoproperty:: map
      .. autoproperty:: element_type


   .. autoclass:: _IncrementableIndexCollection
      :show-inheritance:

      .. rubric:: Magic methods

      .. automethod:: __index__
      .. automethod:: __len__
      .. automethod:: __iter__
      .. automethod:: __lt__
      .. automethod:: __eq__

      .. rubric:: Properties

      .. autoproperty:: base

      .. rubric:: Methods

      .. automethod:: increment

