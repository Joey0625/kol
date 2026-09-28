# 潮流劲抽 YouTube KOL 搜索与筛选

这是一个可在 Windows 本地运行的简体中文桌面应用，用于筛选台湾与香港地区、适合推广潮流劲抽（gachafashion.com）的 YouTube 频道。数据存储在本机 SQLite，不会自动发送邮件、私信或评论。

## 启动

1. 安装 Python 3.11 或更高版本。
2. 在本目录打开 PowerShell，运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

也可以双击 `run.bat` 启动。

首次转发给其他电脑时，先双击 `setup.bat` 创建本地环境并安装依赖，再双击 `run.bat`。

## 配置 YouTube Data API Key

1. 在 Google Cloud Console 创建项目，启用 `YouTube Data API v3`，创建 API Key。
2. 打开程序，在菜单 `设置 > 配置 YouTube API Key` 中粘贴 Key。Key 仅保存在本机 `data/kol_search.sqlite`。
3. 取消勾选“演示数据模式”，选择地区并点击“开始搜索”。也可以通过系统环境变量 `YOUTUBE_API_KEY` 提供 Key。

程序只调用公开的 `search.list`、`channels.list`、`playlistItems.list`、`videos.list` 接口，采集公开频道和公开视频元数据。API 返回的频道会按频道 ID 去重，最近视频默认检查 10 条，详情展示最近 5 条。

## 演示数据模式

首次启动以及未填写 API Key 时会默认启用演示数据模式。它提供台湾、香港和待确认地区的样例档案，涵盖：推广命中、未发现推广、地区判定、风险标记、人工审核和导出流程。演示数据不是实际合作结论。

## 使用说明

- 主列表分为 `A. 已推广过潮流勁抽`、`B. 未发现推广过潮流勁抽` 和单独的 `待确认地区`，后者不会混入正式地区结果。
- 双击一行打开达人档案，可编辑标签、评分、审核状态、备注和收藏标记，也可直接打开频道与公开视频链接。
- 在 `设置 > 管理关键词库` 中可新增分组、删除关键词、批量导入。批量内容支持换行、逗号和分号，重复词会自动去重。
- 点击“导出当前结果”可导出 `.xlsx` 或 UTF-8 BOM `.csv`。导出包括证据链接、检索时间、检索视频数量、来源、采集时间和合规提示。

## 判定与限制

- 地区高置信度来自公开频道/视频/联系资料中的台湾或香港直接表述；本地用语与地点归为中置信度；仅繁体中文归为低置信度且不做地区归属。
- 推广识别检查 `gachafashion.com`、`Gacha Fashion`、`潮流勁抽`、`潮流劲抽` 在公开频道介绍和公开视频标题/说明中的命中。当前 API 流程不能可靠验证口播、置顶评论、优惠码真实性或全部历史视频，均需人工复核。
- `未发现推广过潮流勁抽` 不等于从未推广。涉及儿童、亲子、玩具等词的内容会标记“可能面向未成年人”，合作前仍需确认当地广告披露、抽奖及未成年人营销合规。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

测试覆盖关键词去重、地区判定、推广命中分类及导出字段完整性。

## Windows 免安装版

GitHub Actions 会在 Windows 云端构建机上自动生成单文件 `.exe`。在仓库的 **Actions** 页面运行 “Build Windows application”，完成后从该次运行的 Artifacts 下载 `潮流劲抽-YouTube-KOL工具-Windows`。解压后即可双击 `.exe`；无需安装 Python。

程序会在 `.exe` 所在目录创建 `data/kol_search.sqlite`，用于保存本地档案和 API Key。因此请将程序放在具有写入权限的目录（例如桌面或文档），不要放在 `Program Files`。
