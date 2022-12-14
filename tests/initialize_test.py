#! /usr/bin/env python
from __future__ import annotations

import nzb2media


def test_eol():
    import eol
    eol.check()


def test_cleanup():
    import cleanup
    cleanup.clean(cleanup.FOLDER_STRUCTURE)


def test_import_core():
    pass


def test_import_core_auto_process():
    pass


def test_import_core_plugins():
    pass


def test_import_core_user_scripts():
    pass


def test_import_six():
    pass


def test_import_core_utils():
    pass


def test_initial():
    nzb2media.initialize()
    del nzb2media.MYAPP


def test_core_parameters():
    assert nzb2media.CHECK_MEDIA == 1
