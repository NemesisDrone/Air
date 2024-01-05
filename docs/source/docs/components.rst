Components
==========

Project follows a modular approach. The project is divided in several components,
each one with its own purpose. The following table shows the components and their purpose:

.. list-table::
    :widths: 25 75
    :header-rows: 1

    * - Components
      - Purposes

    * - :doc:`nemesis_utilities <./components/nemesis_utilities>`
      - Exposes the `utilities` library for all reusable code.

    * - :doc:`manager <./components/manager>`
      - Orchestrates the components execution.

    * - :doc:`sim7600 <./components/sim7600>`
      - The sim7600 component is responsible for the gnss positioning.

    * - :doc:`sense_hat <./components/sense_hat>`
      - The sense_hat component is responsible for sensing various data from the sense hat.

    * - :doc:`vl53 <./components/vl53>`
      - The vl53 component is responsible for the distance measurement.