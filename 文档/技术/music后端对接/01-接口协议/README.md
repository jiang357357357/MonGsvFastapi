# 接口协议

用于归档 HTTP API、WebSocket、请求参数、响应结构与对接约定。

- [01-API完整手册.md](./01-API完整手册.md)
- [02-TTS流式WebSocket设计.md](./02-TTS流式WebSocket设计.md)

2026-10-24 已按当前实现核对训练工作台、八版本训练默认值、V5 合成参数与流式限制。HTTP 主业务接口使用 `seed/sample_steps/cfg_rate/inference_mode`；WS 按模型返回 `tokens` 或 `segments`，不接受官方新增 `gpt_streaming`。
