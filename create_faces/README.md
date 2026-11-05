# 表情图片序列控制器

本目录包含一个 Blender Python 脚本，用图片序列创建带骨骼控制器的表情平面，并保存为 `.blend` 文件。脚本针对 Blender 4.4 编写。

## 文件

- `create_eye_plane_driver.py`：生成场景的 Blender Python 脚本。
- `run.ps1`：PowerShell 启动器，会把命令行参数传给 Python 脚本。
- `eye_mouth/`：默认图片素材目录。

## 默认运行

在 PowerShell 中，从项目根目录执行：

```powershell
.\create_faces\run.ps1
```

脚本默认读取 `create_faces/eye_mouth/` 中以 `eye_` 开头的图片，并输出：

```text
create_faces/eye_sequence_driver.blend
```

图片按文件名排序。建议使用连续编号命名，例如 `eye_01.png`、`eye_02.png`、`eye_03.png`。

## 查看帮助

```powershell
.\create_faces\run.ps1 --help
```

## 命令行选项

| 选项 | 说明 | 默认值 |
| --- | --- | --- |
| `--image-dir`、`-d` | 图片所在目录 | `create_faces/eye_mouth/` |
| `--prefix`、`-p` | 图片文件名前缀 | `eye_` |
| `--output`、`-o` | 输出的 `.blend` 文件路径 | `create_faces/eye_sequence_driver.blend` |

例如，使用 `mouth_` 序列并另存到指定位置：

```powershell
.\create_faces\run.ps1 --image-dir "D:\素材\表情" --prefix "mouth_" --output "D:\输出\mouth_driver.blend"
```

短选项也可以这样使用：

```powershell
.\create_faces\run.ps1 -d "D:\素材\表情" -p "mouth_" -o "D:\输出\mouth_driver.blend"
```

也可以直接调用 Blender：

```powershell
& "D:\software\blender-4.4.0-candidate\blender.exe" --background --python "D:\workspaces\codex\blender_scripts\create_faces\create_eye_plane_driver.py" -- --help
```

直接调用时，Python 脚本的参数要写在 Blender 的 `--` 后面。

## 在 Blender 中控制图片

打开生成的 `.blend` 文件后，在 `Expression` 集合中选择控制骨架，进入姿态模式并沿骨骼本地 Y（对应世界 Z）正方向移动：

- 移动范围限制为 `0` 到 `(图片数量 - 1) / 10`。
- 每移动 `0.1` 个单位，图片偏移增加 1 帧。
- 驱动表达式为 `int(bone_y * 10)`。
- 右侧刻度从 1 开始，刻度 1 对齐骨骼头部；每格对应一张图片。

生成脚本会清除当前场景物体、创建表情平面和控制组件，并将 3D 视图设为材质预览。再次运行会重新生成并覆盖同名输出文件。
