import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from koltool.exporter import export_xlsx
from koltool.ui import DetailDialog, MainWindow


def test_demo_search_filter_detail_and_export(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "kols.sqlite")
    window.demo_mode.setChecked(True)
    window.search()
    assert window.tables["promoted"].rowCount() >= 1
    assert window.tables["not_found"].rowCount() >= 1

    window.filter_region.setCurrentText("台湾")
    assert window.tables["unconfirmed"].rowCount() == 0
    channel_id = window.tables["promoted"].item(0, 0).data(256)
    dialog = DetailDialog(window.db, channel_id, window)
    assert "潮流勁抽推广识别" in dialog.info.toPlainText()

    out = export_xlsx(tmp_path / "result.xlsx", window.db.get_profiles())
    assert out.exists() and out.stat().st_size > 0
    dialog.close()
    window.close()
