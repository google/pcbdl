Core Language
=============

.. module:: pcbdl.base

Nets
----

.. autoclass:: pcbdl.Net

    .. method:: __init__(name)

        Nets can be created by calling ``Net("SOME_NAME")``.

        If used in more places, you might want to save it in a variable::

            gnd = Net("GND")

        The name in the "" gets automatically capitalized, but it's good
        practice to do it anyway. Though the variables should stay lowercase
        to conform to the python style guide.

        Also note that the variable names should not necessarily have to match
        the net name. In some cases it might make more sense to have a shorter
        name locally for a net instead of the full long global name. Example:
        ``mosi = Net("AP_SPI2_MOSI")``

    .. automethod:: __lshift__(pin or pins)
    .. automethod:: __rshift__(pin or pins)

        :class:`Pins<Pin>` can be connected to nets using the ``<<`` and ``>>`` operators::

            gnd << device1.GND

        A :term:`list<iterable>` of pins can also be given (and they will be added in the same
        group)::

            gnd << (device1.GND, device2.GND)
            gnd >> (
                device3.GND,
                device4.GND,
            )

        The direction of the arrows is stored, but it doesn't really mean
        anything yet. You're free to use it as a hint on which way the signal
        is flowing (low impedance toward high impedance).

        :returns: A special version of this Net that will actually
            :attr:`remember the group<grouped_connections>` that we're
            currently attaching to. This way Pins added in the same line,
            even if alternating operators, will remember
            they were grouped::

                gnd << device1.GND >> regulator1.GND
                gnd << device2.GND >> regulator2.GND

            Now device1 and regulator1's GND pin are remembered that they were
            grouped. The grouping might be significant, maybe as a hint, to the
            reader. This is a little bit of metadata that allows prettier
            exports (eg: SVG output will probably draw a real wire between
            those pins instead of airwires).

    .. autoproperty:: connections

    .. autoproperty:: grouped_connections

Parts
-----
.. autoclass:: pcbdl.Part

    .. autoattribute:: PINS
    .. autoattribute:: pins
    .. autoattribute:: REFDES_PREFIX
    .. autoattribute:: pin_names_match_nets
    .. autoattribute:: pin_names_match_nets_prefix
    .. autoproperty:: refdes


Pins
----
.. autoclass:: pcbdl.Pin

.. autoclass:: pcbdl.base.PinFragment

.. autoclass:: pcbdl.base.PartClassPin

.. autoclass:: pcbdl.base.PartInstancePin

    .. autoproperty:: net

    .. automethod:: __lshift__(another pin or pins)
    .. automethod:: __rshift__(another pin or pins)

        Syntactic sugar for ``pin.net << another_pin`` or ``pin.net >> another_pin``::

            # Instead of
            Net() >> somepart.BUTTON << somebutton.OUTPUT

            # Or
            Somepart.BUTTON.net << somebutton.OUTPUT

            # One can just write
            somepart.BUTTON << somebutton.OUTPUT


Other
-----

.. .. automodule:: pcbdl.base
..  :members:
