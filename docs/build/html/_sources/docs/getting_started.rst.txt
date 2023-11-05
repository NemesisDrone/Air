Getting Started
===============

Let's get started with Nemesis Air repository. This page will guide you through the project workflow.

System Requirements
^^^^^^^^^^^^^^^^^^^
.. _system_requirements:

On both Windows and Linux, you will need to install the following software:

#. Docker & docker-compose, both installable through `Docker Desktop <https://www.docker.com/products/docker-desktop>`_.
#. Python3 for doc generation, installable through `Python <https://www.python.org/downloads/>`_.
#. The doc python dependencies, installable through ``pip install -r requirements-system.txt``.

These will be the only requirements to run the project.

Run this project
^^^^^^^^^^^^^^^^

Install system requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Refer to the :ref:`System Requirements <system_requirements>` section to install the system requirements.

Docker & Compose
~~~~~~~~~~~~~~~~
Nemesis air is based on docker and docker-compose. The `Dockerfile` is used to build an isolated environment
for the project.

Docker-compose is used to run the project, there is 3 compose files:

#. ``compose.yml``: used to run the project in development mode, your code changes will be reflected in the container without having to rebuild it.
#. ``compose-prod.yml``: used to run the project in production mode, your code changes will not be reflected in the container, you will have to rebuild it.
#. ``compose-test.yml``: same as ``compose.yml`` but with run tests as root.

Run the project using cli
-------------------------

To run the project using cli run this command: ``docker compose up`` in the root directory of the project.
This command will run the dev configuration running the :mod:`manager <src.manager>` module.

You can specify what configuration to run by using the ``-f`` flag,
for example to run the prod configuration run this command: ``docker compose -f compose-prod.yml up``.

The manager module is the entry point of the project, this module will run components depending on the profile,
profiles are hardcoded in the manager module and specify a list of components to run. To specify a profile to run,
prepend your command with c=<profile_name>, for example to run the default profile run this command:
``c=default docker compose up``.

.. note::
    The default profile is the one run by default when running the project without specifying a profile.

You can also use the ``d=1`` flag to run the project in debug mode, this will run the project in debug mode and show
debug logs.

Configure interpreter
---------------------

.. note::
    This step explains how to configure the interpreter using PyCharm, but this is available on other IDEs.

You can use docker-compose to configure your python interpreter, by following these steps, PyCharm will run the docker-compose
configuration and then use the interpreter inside the container. This allows to execute code directly in the container
as if it was executed on the raspberry pi.

1. Go to project settings

.. image:: ../assets/getting_started/1.png
    :width: 50%
    :alt: PyCharm configuration

2. Click on ``Add interpreter`` and then ``Docker-compose``

.. image:: ../assets/getting_started/2.png
    :width: 50%
    :alt: PyCharm configuration

3. The docker server should be automatically detected, click on the configuration file button, then select the
   plus button and select the ``compose.yml`` file.

.. note::
    You can also select the ``compose-test.yml`` file to run the tests in the container.

.. image:: ../assets/getting_started/3.png
    :width: 50%
    :alt: PyCharm configuration

4. To configure env variables, click on the Environment variables button and then fill the name and value fields.

.. image:: ../assets/getting_started/4.png
    :width: 50%
    :alt: PyCharm configuration

.. image:: ../assets/getting_started/5.png
    :width: 50%
    :alt: PyCharm configuration

6. You can name the compose project to avoid conflict.

.. tip::
    If you want to configure the interpreter to directly test code on your system, you can create two interpreter
    using the same compose file with different environment variables. For example you can create a "classic" and a
    "debug" interpreter.

.. image:: ../assets/getting_started/6.png
    :width: 50%
    :alt: PyCharm configuration

7. Wait for the build process and then click on "next", the interpreter should be be automatically detected. If not,
   check if there is no error in the build process.

.. image:: ../assets/getting_started/7.png
    :width: 50%
    :alt: PyCharm configuration

8. You can see all configured interpreters in the bottom right corner of the IDE. You can easily switch between
   interpreters by clicking on the interpreter name.

.. warning::
    There is often some issues leading to the list of symbols not being loaded, if there is errors in your files import
    statements, juste switch to your system interpreter and re-switch to the compose interpreter with this menu.

.. image:: ../assets/getting_started/8.png
    :width: 50%
    :alt: PyCharm configuration

9. If you run a script manually, this script will be executed in the container.

.. image:: ../assets/getting_started/9.png
    :width: 50%
    :alt: PyCharm configuration


Document this project
^^^^^^^^^^^^^^^^^^^^^

To learn how to document this project, please see the `Documentation tutorial <https://github.com/NemesisDrone/Workflow/blob/main/DocTutorial.md>`_.
