# 通信验证 L 灯

记录 2026-10-10 Grove Vision AI V2 与 Arduino Uno R3 的通信及指示灯验证结果。

## 接线和运行方式

V2 通过 I²C 地址 `0x62` 输出检测结果，Uno 使用 A4 接 SDA、A5 接 SCL，5V 和 GND 给 V2 供电。正常运行时只连接 Uno USB，V2 USB 断开。Uno 自带的 L 灯由 `LED_BUILTIN`（D13）控制。

## 验证结果

- 有脸画面：连续 36 次报告 `COUNT=1`，帧号从 103 增至 245，人脸框随移动变化；用户已目视确认 L 灯亮起。
- 无人脸画面：连续 36 次报告 `COUNT=0`，帧号从 484 增至 625；无人脸时 L 灯熄灭尚未单独目视确认。
- 数据停滞：超过两秒没有新帧时，Uno 输出 `WAIT_V2_STALE`，程序将 L 灯设为 LOW。停滞保护已通过串口记录验证。
- 切换供电后曾发生帧号停滞，按 V2 RESET 恢复；根因仍待排查。

串口证据：[有脸](uno-face-present.log)、[无人脸](uno-no-face.log)、[停滞保护](uno-stale-guard.log)。完整结果见 [verification.json](verification.json)，控制程序见 [Uno main.cpp](../uno/src/main.cpp)。
