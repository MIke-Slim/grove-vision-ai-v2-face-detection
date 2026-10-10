# 第三方来源和许可证

| 部分 | 来源 | 许可说明 |
|---|---|---|
| 人脸权重 | https://github.com/akanametov/yolo-face/releases/tag/1.0.0 | 权重来自上游发布；项目许可文本以其仓库为准，副本见 `licenses/Yolo-Face-GPL-3.0.txt` |
| 导出时使用的 Ultralytics 8.0.173 | https://github.com/ultralytics/ultralytics | 本机安装包附带 AGPL-3.0 文本，保存在 `licenses/Ultralytics-AGPL-3.0.txt` |
| Himax SDK | https://github.com/HimaxWiseEyePlus/Seeed_Grove_Vision_AI_Module_V2/tree/d3265e20d75fe20faccbf185d24454ad08b2fda8 | 顶层 MIT 文本保存在 `licenses/Himax-SDK-MIT.txt`；内部组件保留各自的版权与许可 |
| TFLM、Ethos-U、CMSIS 及其他 SDK 内部组件 | 固定 SDK 中的源文件、头文件与预编译库 | 按 SDK 对应组件中的原许可处理，顶层 MIT 文本不替代内部许可 |
| Arm GNU Toolchain | https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads | 准备脚本从上游获取；保留压缩包中的工具及运行库许可 |
| GNU make | https://repo.msys2.org/mingw/mingw64/ | 准备脚本获取 MSYS2 4.4.1-3 包；其包元数据标注 GPL3 |

本工程增加了模型检测头导出、量化流程、自定义后处理、旋转补偿、I²C 数据协议、Uno 接收程序和本地烧录工具。引用或使用第三方权重、源码、库和产物时，其原有许可继续适用。原始相机图片和个人校准图没有进入仓库。

预训练权重未在本工程重新训练；转换和量化不代表对上游权重拥有新的授权。仓库提供来源、版本、校验值及构建步骤，未赋予统一的第三方商业使用授权。
