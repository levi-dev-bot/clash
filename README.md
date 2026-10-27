# clash

Clash / mihomo 规则集。源自 [lee-win/clash](https://github.com/lee-win/clash)，已重构。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `Clash-LIAN.ini` | OpenClash / subconverter 规则模板（策略组 + ruleset 定义） |
| `AI.list` | AI 服务风控严名单 · 域名部分（171 条） |
| `AI-IP.list` | AI 服务风控严名单 · IP 部分（9 条，IP-CIDR / IP-ASN） |
| `Airport.list` | 机场域名（订阅/官网走代理） |
| `Proxy.list` | 国外代理补充 + 国外 DNS |
| `Direct.list` | 国内直连补充 |
| `Download.list` | 国内下载直连 |
| `relay.list` | 中转域名 |
| `Clash-Dev.txt` | OpenClash 开发者选项自定义脚本 |

## AI.list 数据源

融合版，180 条，源自：

- [VPSDance/ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules)（每日自动同步）
- [Repcz/Tool](https://github.com/Repcz/Tool)（补充）

覆盖：OpenAI / ChatGPT / Sora、Anthropic / Claude、Google Gemini / AI Studio、Meta AI / Muse / Llama、xAI / Grok、Microsoft Copilot / GitHub Copilot、Perplexity、Poe。

**含风控关键域名**（一般规则集容易漏）：

- `arkoselabs.com` —— 人机验证
- `statsig.com` / `featuregates.org` / `launchdarkly.com` / `growthbook.io` —— 特征开关（指纹）
- `datadog` / `sentry` / `sift` —— 反欺诈上报
- `auth0.com` —— 登录
- `stripe.com` —— 支付
- `livekit.cloud` —— 语音

对应 QX 三段式版本：[quantumultx-rules](https://github.com/levi-dev-bot/quantumultx-rules)

## 用法

### OpenClash

订阅转换时把模板地址指向本仓库：

```
https://raw.githubusercontent.com/levi-dev-bot/clash/refs/heads/main/Clash-LIAN.ini
```

### mihomo rule-providers

```yaml
rule-providers:
  AI-Domain:
    type: http
    behavior: domain
    url: https://raw.githubusercontent.com/levi-dev-bot/clash/refs/heads/main/AI.list
    path: ./providers/ai_domain.yaml
    interval: 86400
  AI-IP:
    type: http
    behavior: ipcidr
    url: https://raw.githubusercontent.com/levi-dev-bot/clash/refs/heads/main/AI-IP.list
    path: ./providers/ai_ip.yaml
    interval: 86400

rules:
  - RULE-SET,AI-Domain,AI
  - RULE-SET,AI-IP,AI,no-resolve
```

## 相对原版的改动

1. **AI 规则**：从 26 条扩到 180 条，补齐风控域名和 Meta/xAI/Perplexity/Poe
2. **IP 规则拆文件**：mihomo 一个 rule-provider 只能有一种 behavior，IP 类必须单独拆，否则加载报错
3. **新增「美国-固定」组**：`fallback` + 3600s 探活，出口不按延迟漂移（`url-test` 会导致出口 IP 频繁跳变，是 AI 账号风控的负面信号）
4. **AI 组默认选中「美国-固定」**：原版默认 `DIRECT`，AI 流量直连会暴露真实 IP
5. **排除项**：美国节点里的 `V6`（IPv6 通道）、`专线` / `IPLC`（入口在国内福州 `222.79.111.x`，落地未知）不进 AI 组

## 注意

- 本仓库的 `AI.list` 不含策略名，策略在规则引用处指定
- IP 规则必须带 `no-resolve`，否则触发额外 DNS 解析
- `Clash-LIAN.ini` 里的节点名匹配依赖机场命名习惯；换机场需要核对正则
