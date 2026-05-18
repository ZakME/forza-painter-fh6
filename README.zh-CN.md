# forza-painter FH6

[English](README.md) | [中文](README.zh-CN.md)

把图片生成 Forza Horizon 6 可导入的 Vinyl Group 图层。

这个工具包含两部分：

- 使用 GPU/OpenCL 生成 geometry JSON。
- 把 JSON 写入当前打开的 FH6 Vinyl Group Editor。

正常使用不需要手动填写内存地址。导入 FH6 时只需要选择游戏进程、填写模板层数，然后点击导入。

## 安装

1. 下载本仓库 ZIP，并解压。
2. 安装 64 位 Python，推荐 Python 3.12。
3. 打开解压后的文件夹。
4. 双击 `install_dependencies.bat`。
5. 双击 `start_app.bat` 启动软件。

如果打开失败，先运行 `check_environment.bat` 检查 Python 依赖。

## 生成 JSON

1. 进入 `Generate JSON` 页面。
2. 点击 `Add images` 添加 PNG/JPG/BMP 图片。
3. 选择一个品质预设。
4. 可选：勾选 `Use custom settings`，在软件内修改输出层数、分辨率、随机样本和变异样本。
5. 点击底部固定的 `Start generating`。
6. 等待右侧预览和日志更新。

生成文件会保存在原图片旁边，例如：

```text
image.500.json
image.1000.json
image.3000.json
```

生成页左侧可以滚动。窗口较小时，`Start generating` 按钮会固定在左侧底部，不需要向下找。

## 品质和自定义参数

预设越靠后通常越慢，质量越高。

- `extremely fast`：快速测试构图。
- `fast`：较快生成可用结果。
- `balanced`：默认推荐。
- `slow`：更高质量。
- `super slow`：更慢，适合最终输出。

自定义参数只影响本次生成，不会改动原始预设文件。常用参数含义：

- `Output layers`：最多生成多少层。
- `Max resolution`：生成器处理图片时的最大分辨率。
- `Random samples`：随机候选数量，越高越慢。
- `Mutated samples`：变异优化数量，越高越慢。
- `Save checkpoints`：保存哪些层数的 JSON，例如 `500,1000,1500,3000`。

## 准备 FH6

1. 启动 Forza Horizon 6。
2. 进入 `Create Vinyl Group` / `Vinyl Group Editor`。
3. 加载一个由大量简单 sphere 图层组成的模板。
4. 把模板 `Ungroup`。
5. 记住游戏里显示的真实层数。
6. 导入时保持这个编辑器打开，不要切换菜单。

推荐模板大小：500 到 3000 层。

## 导入 JSON

1. 进入 `Import` 页面。
2. 点击 `Refresh`，选择正在运行的 `forzahorizon6.exe`。
3. 填写游戏里当前模板的真实层数。
4. 添加生成好的 `.json`，或者点击 `Use generated JSON`。
5. 高级地址输入框保持空白。
6. 点击 `Import JSON`。

软件会先定位并验证当前 FH6 图层表。无法安全确认目标时会在写入前停止。

## 必须注意

- 模板必须已经 `Ungroup`。
- 软件里的层数必须和游戏里的层数完全一致。
- 导入过程中不要切换游戏菜单。
- 重启游戏、重新加载模板、改变模板层数后，请重新填写正确层数再导入。
- JSON 比模板小：未使用的模板层会被隐藏。
- JSON 比模板大：超出的图形会被裁剪。
- 透明 PNG 的透明背景不会作为可见底色导入。

## 常见问题

### GPU 生成器或 OpenCL 报错

更新 NVIDIA/AMD/Intel 显卡驱动。生成器是 `forza-painter-geometrize-go.exe`，依赖 OpenCL。

### 找不到 Python 或依赖缺失

运行：

```powershell
install_dependencies.bat
```

再运行：

```powershell
check_environment.bat
```

出现 `Core OK` 说明 Python 依赖正常。

### `_ARRAY_API not found`、NumPy 或 OpenCV 报错

这是可选预览依赖问题，不影响生成 JSON 或导入 FH6。优先重新安装核心依赖：

```powershell
python -m pip install -r requirements.txt
```

### `OpenProcess` 或权限错误

关闭软件，用管理员身份运行 `start_app.bat`。

生成 JSON 不需要管理员权限，导入 FH6 通常需要管理员权限。

### 找不到游戏进程

先打开 FH6，再点击 `Refresh`。如果仍然没有，重启软件。

### 定位不到安全模板

检查：

- 当前在 Vinyl Group Editor。
- 模板已经 Ungroup。
- 层数填写完全正确。
- 填写层数后没有切换菜单。

### 导入效果被截断

模板层数不够。换更大的模板，或者生成更少层数的 JSON。

## 文件说明

普通用户只需要这些文件：

- `install_dependencies.bat`：安装 Python 依赖。
- `start_app.bat`：启动软件。
- `check_environment.bat`：检查环境。
- `clean_runtime_data.bat`：发布或重新压缩前清理运行缓存。
- `1. drag_image_file_here.bat`：可选，把图片拖上去打开软件。

不要上传或发布运行缓存目录，例如 `webui-data`、`runtime`、`__pycache__`、`dist`。
