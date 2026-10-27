# clash — OpenClash / mihomo 规则与策略组

源自 [lee-win/clash](https://github.com/lee-win/clash)，已重构。**OpenWrt 上的 OpenClash 直接从这里拉规则。**

## 文件

| 文件 | 用途 |
|---|---|
| `AI.list` | AI 风控严名单（域名），171 条。classical 文本格式 |
| `AI-IP.list` | AI 风控 IP 段，6 条。classical 文本格式，**不含 IP-ASN**（见下方坑） |
| `Clash-LIAN.ini` | subconverter 模板，含 18 个策略组 |
| `Airport.list` | 机场域名（走 Airport 组，避免机场面板流量走代理） |
| `Proxy.list` | 需代理的零散域名 |
| `Direct.list` | 直连名单 |
| `Download.list` / `relay.list` | 下载 / 中转 |

## 规则格式

`AI.list` 和 `AI-IP.list` 是 **classical 纯文本**，不是 YAML payload。mihomo 和 subconverter 都能直接吃：

```yaml
rule-providers:
  AI-Domain:
    type: http
    behavior: classical
    format: text          # ← 必须写，否则按 YAML 解析会失败
    url: https://raw.githubusercontent.com/levi-dev-bot/clash/refs/heads/main/AI.list
    path: ./rule_provider/ai_domain.yaml
    interval: 86400
  AI-IP:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/levi-dev-bot/clash/refs/heads/main/AI-IP.list
    path: ./rule_provider/ai_ip.yaml
    interval: 86400
rules:
  - RULE-SET,AI-Domain,AI
  - RULE-SET,AI-IP,AI,no-resolve
```

subconverter 用 `ruleset=AI,<URL>` 即可，无需转换。

## 实测过的坑

**① rule-provider 里不能有 IP-ASN**
只要文件里出现一行 `IP-ASN,xxx`，整个 provider 报 `ASN invalid, remove and download` 并**归零**（ruleCount=0）。IP-ASN 必须内联在 `rules:` 里，且运行目录要有 `ASN.mmdb`。

**② subconverter 的 `custom_proxy_group` filter 里不能写 `\|`**
`(美国0[1-9]|美国\|0[1-9])` 会让**整个 filter 失效**，组里只剩 `DIRECT`。改用 `[|]` 字符类也一样失败。要匹配含 `|` 的节点名（如 naiko 的 `美国|01`）只能拆成独立组。

**③ `udp=false` 会静默过滤节点**
订阅转换 URL 带 `udp=false` 时，hysteria2 / anytls 类节点被整体剔除。pokemon 的 `美国0X原生`（hysteria2）和 naiko 的 `美国|0X`（anytls）都会消失，只剩 trojan 的 V6 节点。

**④ api.wcc.best 有强缓存**
改完 ini 后转换器仍返回旧结果，等 5 分钟也不刷。给 `config` 参数加 `?t=<时间戳>` 才生效。

## 策略组设计

AI 组走 `美国-固定`（`fallback` + 3600s 探活），不用 `url-test`——`url-test` 按延迟重排会让出口 IP 漂移，这本身是风控负面信号。

```
AI → 美国-固定 → (fallback) 美国0X丨V6 / 美国0X原生
```

## 相关

- 节点质量实测：`~/.hermes/scripts/ip_health_check.py`
- 上游规则源：VPSDance/ai-proxy-rules、Repcz/Tool、blackmatrix7/ios_rule_script

## mihomo vs subconverter：filter 正则不通用

| 场景 | 匹配 `美国|01` | 结果 |
|---|---|---|
| mihomo `proxy-groups[].filter` | `"(美国\\\\|0[1-9])"` (YAML 四个反斜杠) | ✅ |
| subconverter `custom_proxy_group` | `(美国\|0[1-9])` | ❌ 整个 filter 归零 |
| subconverter | `(美国[|]0[1-9])` | ❌ 同样归零 |

mihomo 直连配置（`config/merged.yaml`）能混着写；subconverter 里必须把含 `|` 的节点单独建组。

## OpenClash 的 jsdelivr 改写会拼错路径

`github_address_mod = https://fastly.jsdelivr.net/` 时，OpenClash 把
`raw.githubusercontent.com/用户/仓库/refs/heads/main/文件` 改写成
`fastly.jsdelivr.net/gh/用户/仓库@refs/heads/main/文件` → **404**（正确是 `@main`）。

首次启动 provider 可能拉取失败，第二次重启会回退直连 raw.githubusercontent.com 就好了。
要根治就把 `github_address_mod` 设 `0`。
