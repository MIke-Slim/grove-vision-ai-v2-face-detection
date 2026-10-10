# Grove Vision AI V2 人脸检测子工程

完整工作流、环境安装、硬件接线、模型转换、编译、烧录、数据协议、实测边界和排错说明统一维护在 [仓库根 README](../README.md)。所有命令从仓库根目录执行。

- `firmware/`：V2 推理、后处理及 I²C 接口。
- `uno/`：Uno 独立 PlatformIO 读取工程。
- `tools/`：环境准备、模型转换、构建、烧录、读取和校验工具。
- `models/`：固定权重及已提交的模型产物。
- `artifacts/v2-face-tested.img`：已烧录并完成实物验证的默认固件。
- `artifacts/v2-face-rebuilt.img`：重新编译产物，尚未重新烧录验证。
- `artifacts/uno-face.hex`：已验证的 Uno 读取程序。
- `evidence/`：不含照片的实测记录。
- `manifest.json`：模型和固件校验清单。
- `sources.lock.json`：固定版本的 SDK、编译器和 make 来源。

本机虚拟环境、工具解压目录、缓存、私人校准图片及原始日志仍保存在本地并由 Git 忽略。GitHub 克隆后按根 README 的准备脚本恢复依赖。模型重新量化后要重新编译配套固件，并用 `--firmware face_detection/artifacts/v2-face-rebuilt.img` 明确选择新产物。
