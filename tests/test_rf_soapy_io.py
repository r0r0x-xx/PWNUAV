import numpy as np
import pytest

import pwnuav.rf.soapy_io as sio


def test_module_imports_without_soapy():
    # import must succeed even when SoapySDR is absent
    assert hasattr(sio, "HAVE_SOAPY")
    assert isinstance(sio.HAVE_SOAPY, bool)


def test_sink_and_source_classes_exist():
    assert hasattr(sio, "SdrSink")
    assert hasattr(sio, "SdrSource")


@pytest.mark.skipif(sio.HAVE_SOAPY, reason="SoapySDR present; skip absence check")
def test_instantiation_without_soapy_raises_clear_error():
    with pytest.raises(RuntimeError, match="SoapySDR"):
        sio.SdrSink()
    with pytest.raises(RuntimeError, match="SoapySDR"):
        sio.SdrSource()
