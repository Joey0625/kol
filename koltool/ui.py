from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from .database import Database
from .demo import profiles as demo_profiles
from .exporter import export_csv, export_xlsx
from .keywords import parse_bulk_keywords
from .youtube import YouTubeApiError, YouTubeClient


# In a PyInstaller build, application modules are unpacked to a temporary
# directory.  User-created data must live beside the executable instead.
ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def _num(value: int) -> str:
    return f"{value:,}"


class KeywordDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("关键词库配置")
        self.resize(660, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("关键词按分组管理。批量导入可用换行、逗号或分号分隔，重复词会自动去重。"))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["分组", "关键词"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        form = QGridLayout()
        self.group = QComboBox(); self.group.setEditable(True)
        self.bulk = QPlainTextEdit(); self.bulk.setPlaceholderText("例如：一番賞开箱，模型开箱\nPokemon PSA")
        form.addWidget(QLabel("分组"), 0, 0); form.addWidget(self.group, 0, 1)
        form.addWidget(QLabel("新增/批量导入"), 1, 0); form.addWidget(self.bulk, 1, 1)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        add = QPushButton("新增/导入"); add.clicked.connect(self.add)
        delete = QPushButton("删除选中"); delete.clicked.connect(self.delete)
        close = QPushButton("关闭"); close.clicked.connect(self.accept)
        buttons.addWidget(add); buttons.addWidget(delete); buttons.addStretch(); buttons.addWidget(close)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self):
        groups = self.db.keyword_groups()
        self.group.clear(); self.group.addItems(groups)
        rows = [(group, term) for group, terms in self.db.keywords().items() for term in terms]
        self.table.setRowCount(len(rows))
        for row, (group, term) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(group))
            self.table.setItem(row, 1, QTableWidgetItem(term))
        self.table.resizeColumnsToContents()

    def add(self):
        group = self.group.currentText().strip()
        terms = parse_bulk_keywords(self.bulk.toPlainText())
        if not group or not terms:
            QMessageBox.information(self, "关键词库", "请填写分组和至少一个关键词。")
            return
        self.db.add_keywords(group, terms)
        self.bulk.clear(); self.refresh()

    def delete(self):
        rows = sorted({item.row() for item in self.table.selectedItems()}, reverse=True)
        for row in rows:
            item = self.table.item(row, 1)
            if item:
                self.db.delete_keyword(item.text())
        self.refresh()


class DetailDialog(QDialog):
    def __init__(self, db: Database, channel_id: str, parent=None):
        super().__init__(parent)
        self.db, self.channel_id = db, channel_id
        self.profile = db.get_profile(channel_id)
        self.setWindowTitle("达人档案")
        self.resize(900, 680)
        layout = QVBoxLayout(self)
        self.info = QTextBrowser(); self.info.setOpenExternalLinks(True)
        layout.addWidget(self.info, 1)
        editor = QGroupBox("人工审核")
        form = QFormLayout(editor)
        self.tags = QLineEdit("、".join(self.profile["tags"]))
        self.score = QSpinBox(); self.score.setRange(0, 100); self.score.setValue(self.profile["score"])
        self.status = QComboBox(); self.status.addItems(["待联系", "已联系", "已回复", "不合作", "已合作"]); self.status.setCurrentText(self.profile["review_status"])
        self.note = QPlainTextEdit(self.profile["note"]); self.note.setMaximumHeight(70)
        self.favorite = QCheckBox("收藏标记"); self.favorite.setChecked(self.profile["favorite"])
        form.addRow("内容标签", self.tags); form.addRow("合作匹配度", self.score); form.addRow("审核状态", self.status); form.addRow("备注", self.note); form.addRow("", self.favorite)
        layout.addWidget(editor)
        buttons = QDialogButtonBox()
        save = buttons.addButton("保存审核", QDialogButtonBox.ButtonRole.AcceptRole); save.clicked.connect(self.save)
        open_channel = buttons.addButton("打开频道", QDialogButtonBox.ButtonRole.ActionRole); open_channel.clicked.connect(lambda: webbrowser.open(self.profile["channel_url"]))
        close = buttons.addButton("关闭", QDialogButtonBox.ButtonRole.RejectRole); close.clicked.connect(self.reject)
        layout.addWidget(buttons)
        self.render()

    def render(self):
        p = self.profile
        video_lines = "".join(f"<li><a href='{v['url']}'>{v['title']}</a> | {v['published_at']} | {_num(v['views'])} 次观看</li>" for v in p["videos"])
        evidence = "<br>".join(f"<a href='{e.get('url', '')}'>{e['title']}</a>：{'、'.join(e['hits'])}<br>{e.get('excerpt', '')}" for e in p["evidence"]) or "未发现。注意：未发现不等于从未推广。"
        contacts = "<br>".join(p["contacts"]) or "未发现公开联系入口"
        risk = "是，涉及亲子/儿童/玩具内容，需人工确认受众与营销合规。" if p["minor_risk"] else "未触发关键词风险标记"
        self.info.setHtml(f"""
        <h2>{p['channel_name']}</h2><p><a href='{p['channel_url']}'>{p['channel_url']}</a><br>频道 ID：{p['channel_id']}</p>
        <h3>地区与数据来源</h3><p>{p['region']}（{p['region_confidence']}置信度）<br>{p['region_basis']}<br>来源：{p['source']}<br>采集时间：{p['sourced_at']}</p>
        <h3>指标</h3><p>订阅 {_num(p['subscribers'])} | 总视频 {_num(p['total_videos'])} | 近90天 {p['posts_90']} 条 | 近期平均观看 {_num(p['avg_views'])} | 互动率估算 {p['engagement_rate']:.2%}</p>
        <p>标签：{'、'.join(p['tags']) or '未标记'}<br>公开联系入口：{contacts}</p>
        <h3>潮流勁抽推广识别</h3><p><b>{p['promotion_status']}</b><br>检索时间：{p['checked_at']}；检索视频：{p['scanned_videos']} 条<br>{evidence}</p>
        <h3>最近相关视频</h3><ol>{video_lines}</ol>
        <h3>评分与合规</h3><p>{p['score']} 分：{p['score_reason']}<br>可能面向未成年人风险：{risk}<br>需确认当地广告披露、抽奖及未成年人营销合规。</p>
        """)

    def save(self):
        tags = [part.strip() for part in self.tags.text().replace("，", "、").split("、") if part.strip()]
        self.db.update_review(self.channel_id, tags, self.score.value(), self.status.currentText(), self.note.toPlainText().strip(), self.favorite.isChecked())
        self.profile = self.db.get_profile(self.channel_id)
        self.render()
        self.accept()


class MainWindow(QMainWindow):
    COLUMNS = ["收藏", "频道名称", "地区", "置信度", "标签", "订阅数", "近90天", "平均观看", "互动率", "评分", "审核状态", "未成年人风险", "数据来源"]

    def __init__(self, db_path: Path | None = None):
        super().__init__()
        self.db = Database(db_path or DATA_DIR / "kol_search.sqlite")
        self.setWindowTitle("潮流劲抽 · YouTube KOL 搜索与筛选")
        self.resize(1440, 850)
        self._create_menu()
        self._build()
        self.seed_demo_if_needed()
        self.refresh()

    def _create_menu(self):
        settings = self.menuBar().addMenu("设置")
        api = QAction("配置 YouTube API Key", self); api.triggered.connect(self.configure_api)
        keyword = QAction("管理关键词库", self); keyword.triggered.connect(lambda: KeywordDialog(self.db, self).exec())
        settings.addAction(api); settings.addAction(keyword)
        help_menu = self.menuBar().addMenu("说明")
        about = QAction("数据范围与合规说明", self); about.triggered.connect(self.show_compliance)
        help_menu.addAction(about)

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        banner = QLabel("仅使用公开 YouTube 数据。推广识别当前核验频道与近期公开视频的标题/说明；口播、置顶评论和合作关系均需人工复核。")
        banner.setWordWrap(True); banner.setObjectName("notice")
        layout.addWidget(banner)
        search = QGroupBox("检索条件")
        grid = QGridLayout(search)
        self.mode = QComboBox(); self.mode.addItems(["关键词", "频道", "视频"])
        self.query = QLineEdit(); self.query.setPlaceholderText("可输入频道名、视频主题或自定义关键词（留空则按关键词库搜索）")
        self.region = QComboBox(); self.region.addItems(["台湾", "香港"])
        self.min_subs = QSpinBox(); self.min_subs.setRange(0, 100000000); self.min_subs.setSingleStep(1000)
        self.min_posts = QSpinBox(); self.min_posts.setRange(0, 90)
        self.min_views = QSpinBox(); self.min_views.setRange(0, 100000000); self.min_views.setSingleStep(1000)
        self.max_results = QSpinBox(); self.max_results.setRange(1, 100); self.max_results.setValue(20)
        self.demo_mode = QCheckBox("演示数据模式"); self.demo_mode.setChecked(not bool(self.db.get_setting("youtube_api_key")))
        run = QPushButton("开始搜索"); run.clicked.connect(self.search)
        labels = [("检索方式", self.mode), ("关键词/频道/视频", self.query), ("地区", self.region), ("最低订阅数", self.min_subs), ("近90天最低发片数", self.min_posts), ("最低平均观看量", self.min_views), ("最多结果", self.max_results)]
        for idx, (label, widget) in enumerate(labels):
            grid.addWidget(QLabel(label), idx // 4, (idx % 4) * 2); grid.addWidget(widget, idx // 4, (idx % 4) * 2 + 1)
        grid.addWidget(self.demo_mode, 2, 0, 1, 2); grid.addWidget(run, 2, 6, 1, 2)
        layout.addWidget(search)
        filters = QHBoxLayout()
        self.filter_region = QComboBox(); self.filter_region.addItems(["全部地区", "台湾", "香港", "无法确认"])
        self.filter_confidence = QComboBox(); self.filter_confidence.addItems(["全部置信度", "高", "中", "低", "无法确认"])
        self.filter_status = QComboBox(); self.filter_status.addItems(["全部审核状态", "待联系", "已联系", "已回复", "不合作", "已合作"])
        self.filter_kind = QComboBox(); self.filter_kind.addItems(["全部类别", "潮玩/手办", "卡牌", "玩具/亲子"])
        self.filter_min_subs = QSpinBox(); self.filter_min_subs.setRange(0, 100000000); self.filter_min_subs.setPrefix("订阅 >= ")
        self.filter_min_views = QSpinBox(); self.filter_min_views.setRange(0, 100000000); self.filter_min_views.setPrefix("平均观看 >= ")
        for widget in [self.filter_region, self.filter_confidence, self.filter_status, self.filter_kind, self.filter_min_subs, self.filter_min_views]:
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(lambda _index: self.refresh())
            else:
                widget.valueChanged.connect(lambda _value: self.refresh())
            filters.addWidget(widget)
        filters.addStretch()
        export = QPushButton("导出当前结果"); export.clicked.connect(self.export)
        filters.addWidget(export)
        layout.addLayout(filters)
        self.tabs = QTabWidget(); self.tables = {}
        for key, title in [("promoted", "A. 已推广过潮流勁抽"), ("not_found", "B. 未发现推广过潮流勁抽"), ("unconfirmed", "待确认地区")]:
            table = QTableWidget(0, len(self.COLUMNS)); table.setHorizontalHeaderLabels(self.COLUMNS); table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSortingEnabled(False); table.cellDoubleClicked.connect(lambda row, col, t=table: self.open_detail(t, row)); table.horizontalHeader().setStretchLastSection(True)
            self.tables[key] = table; self.tabs.addTab(table, title)
        layout.addWidget(self.tabs, 1)
        self.statusBar().showMessage("本地数据库：data/kol_search.sqlite")
        self.setStyleSheet("QGroupBox { font-weight: 600; } #notice { background: #FFF4CE; border: 1px solid #E7C65C; padding: 8px; } QTableWidget { gridline-color: #D9E2F3; } QPushButton { min-height: 28px; }")

    def seed_demo_if_needed(self):
        if self.db.get_profiles():
            return
        words = [word for terms in self.db.keywords().values() for word in terms]
        for profile in demo_profiles(words):
            self.db.upsert_profile(profile)

    def configure_api(self):
        value, ok = QInputDialog.getText(self, "YouTube Data API Key", "API Key（仅保存到本机 SQLite；也可设置环境变量 YOUTUBE_API_KEY）：", QLineEdit.EchoMode.Password, self.db.get_setting("youtube_api_key"))
        if ok:
            self.db.set_setting("youtube_api_key", value.strip())
            self.demo_mode.setChecked(not bool(value.strip()))

    def show_compliance(self):
        QMessageBox.information(self, "数据范围与合规说明", "本工具仅保存公开频道/视频元数据与公开联系入口，不采集非公开个人资料。不会自动发送私信、邮件或评论。\n\n“未发现推广过潮流勁抽”仅代表当前检索范围内未命中，不等于从未推广。涉及抽奖、卡牌、玩具的内容会标注可能面向未成年人风险。导出名单需确认当地广告披露、抽奖及未成年人营销合规。")

    def search(self):
        words = [word for terms in self.db.keywords().values() for word in terms]
        try:
            if self.demo_mode.isChecked():
                found = demo_profiles(words)
                source = "内置演示数据"
            else:
                client = YouTubeClient(self.db.get_setting("youtube_api_key"))
                found = client.discover(words, "TW" if self.region.currentText() == "台湾" else "HK", self.max_results.value(), self.mode.currentText(), self.query.text())
                source = "YouTube Data API"
            accepted = 0
            for profile in found:
                if profile["subscribers"] >= self.min_subs.value() and profile["posts_90"] >= self.min_posts.value() and profile["avg_views"] >= self.min_views.value():
                    self.db.upsert_profile(profile); accepted += 1
            self.refresh()
            self.statusBar().showMessage(f"{source} 完成：发现 {len(found)} 个去重频道，保存 {accepted} 个符合门槛的档案。", 9000)
        except YouTubeApiError as exc:
            QMessageBox.warning(self, "搜索失败", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "搜索异常", f"搜索未完成：{exc}")

    def _filtered(self, profiles: list[dict]) -> list[dict]:
        region, confidence, status, kind = self.filter_region.currentText(), self.filter_confidence.currentText(), self.filter_status.currentText(), self.filter_kind.currentText()
        result = []
        for p in profiles:
            if region != "全部地区" and p["region"] != region: continue
            if confidence != "全部置信度" and p["region_confidence"] != confidence: continue
            if status != "全部审核状态" and p["review_status"] != status: continue
            if p["subscribers"] < self.filter_min_subs.value() or p["avg_views"] < self.filter_min_views.value(): continue
            tag_text = " ".join(p["tags"]).casefold()
            if kind == "潮玩/手办" and not any(x in tag_text for x in ["手办", "手辦", "模型", "公仔", "盲盒", "潮玩", "一番"]): continue
            if kind == "卡牌" and not any(x in tag_text for x in ["卡牌", "pokemon", "psa", "ptcg"]): continue
            if kind == "玩具/亲子" and not any(x in tag_text for x in ["玩具", "亲子", "親子"]): continue
            result.append(p)
        return result

    def refresh(self):
        profiles = self._filtered(self.db.get_profiles())
        groups = {"promoted": [], "not_found": [], "unconfirmed": []}
        for profile in profiles:
            if profile["region"] == "无法确认": groups["unconfirmed"].append(profile)
            elif profile["promotion_status"] == "已推广过潮流勁抽": groups["promoted"].append(profile)
            else: groups["not_found"].append(profile)
        for key, records in groups.items():
            table = self.tables[key]; table.setRowCount(len(records)); table.setProperty("profiles", records)
            for row, p in enumerate(records):
                values = ["★" if p["favorite"] else "", p["channel_name"], p["region"], p["region_confidence"], "、".join(p["tags"][:4]), _num(p["subscribers"]), str(p["posts_90"]), _num(p["avg_views"]), f"{p['engagement_rate']:.1%}", str(p["score"]), p["review_status"], "需确认" if p["minor_risk"] else "", p["source"]]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole, p["channel_id"])
                    table.setItem(row, col, item)
            table.resizeColumnsToContents()
            label = {"promoted": "A. 已推广过潮流勁抽", "not_found": "B. 未发现推广过潮流勁抽", "unconfirmed": "待确认地区"}[key]
            self.tabs.setTabText(self.tabs.indexOf(table), f"{label} ({len(records)})")

    def open_detail(self, table: QTableWidget, row: int):
        item = table.item(row, 0)
        if not item: return
        DetailDialog(self.db, item.data(Qt.ItemDataRole.UserRole), self).exec()
        self.refresh()

    def export(self):
        profiles = self._filtered(self.db.get_profiles())
        if not profiles:
            QMessageBox.information(self, "导出", "当前筛选条件下没有可导出的达人档案。")
            return
        path, selected = QFileDialog.getSaveFileName(self, "导出达人名单", str(ROOT / "exports" / "潮流劲抽_YouTube达人名单.xlsx"), "Excel 工作簿 (*.xlsx);;CSV 文件 (*.csv)")
        if not path: return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        try:
            output = export_csv(path, profiles) if path.lower().endswith(".csv") else export_xlsx(path if path.lower().endswith(".xlsx") else path + ".xlsx", profiles)
            self.statusBar().showMessage(f"已导出 {len(profiles)} 条档案：{output}", 10000)
            QMessageBox.information(self, "导出完成", f"已导出 {len(profiles)} 条档案。\n\n{output}\n\n文件已附带合规提示；未发现推广不等于从未推广。")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("潮流劲抽 YouTube KOL 搜索")
    window = MainWindow(); window.show()
    sys.exit(app.exec())
