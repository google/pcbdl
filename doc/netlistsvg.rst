NetlistSVG
==========

Introduction
------------
`netlistsvg <https://github.com/nturley/netlistsvg>`_ is used by pcbdl to render a graphical output of the schematics.

It uses the "analog skin" to get something similar to what an engineer would draw for a board/pcb level design:

.. figure:: https://raw.githubusercontent.com/nturley/netlistsvg/master/doc/and.svg?sanitize=true

    Netlistsvg's Analog Example
    (TODO: replace drawing with a compact pcbdl example)


Installation
------------

netlistsvg is written in javascript, to run it one needs both nodejs or npm.
For debian style systems the following should do:

.. code-block:: bash

    sudo apt install nodejs npm

One should plan for a location to install netlisvg, I recomend next to the pcbdl folder.

I recommend grabbing the https://github.com/amstan/netlistsvg/tree/for-pcbdl branch.
It has a few tweaks that make netlistsvg outputs so much better, but the changes still need to be
merged with the upstream project.

.. code-block:: bash

    git clone -b for-pcbdl https://github.com/amstan/netlistsvg.git

Then it can be installed with npm:

.. code-block:: bash

    cd netlistsvg
    npm install .

Finally pcbdl neets to be told where netlistsvg is, this is done using an `env variable <https://en.wikipedia.org/wiki/Environment_variable>`_.
The default is assumed to be `~/netlistsvg`. The following can be added to .bashrc or where the user normally stores env variables::

    export NETLISTSVG_LOCATION=~/path/to/installed/netlistsvg

It can be tested by running :code:`make gh-pages` in `pcbdl/`, a bunch of `.svg` files will be created in `examples/`.
