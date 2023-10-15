Nemesis utilities
=================

.. _docs/components/nemesis_utilities:


.. toctree::
    :maxdepth: 1
    :hidden:

    IPC Module <nemesis_utilities/ipc>
    Component Module <nemesis_utilities/component>


How to use
----------

`nemesis_utilities` is the component exposing the `utilities` library for all reusable code.
To use modules from `utilities` in your code, you can import them as follows:

.. code-block:: python

    from utilities import <module_name>

.. tip::
    The library is automatically installed and therefore available to your code ase long as you run it in the Docker
    container.

Modules
-------

.. list-table::
    :widths: 25 75
    :header-rows: 1

    * - Modules
      - Purposes

    * - :ref:`ipc <docs/components/nemesis_utilities/ipc>`
      - Exposes the `IpcNode` class used by each component to communicate together.

    * - :ref:`component <docs/components/nemesis_utilities/component>`
      - Exposes the `Component` class used to create a microservice running in its own process.

