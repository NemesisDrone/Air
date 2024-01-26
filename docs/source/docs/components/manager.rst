The Manager
===========

Abstract
--------

Nemesis Air follows a components-based architecture. Every part of the project run as a
:class:`Component <src.nemesis_utilities.utilities.component.Component>` object. A component is initialized, starts and then stops.
These states changed are managed by the :class:`Manager <src.nemesis_utilities.utilities.manager.Manager>` object.
