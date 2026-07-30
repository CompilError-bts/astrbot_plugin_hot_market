# 热搜交易所

把 60s API 的各平台热搜分别变成独立的虚拟股市。微博话题只在微博股市交易，B站、百度、抖音等市场互不合并。

## 安装

在 AstrBot WebUI 的插件管理页使用以下仓库地址安装：

```text
https://github.com/CompilError-bts/astrbot_plugin_hot_market
```

当前版本是用于验证玩法的 MVP：

- 后台按配置周期采集行情，默认 10 分钟。
- 默认启用微博、百度、B站和抖音。
- 根据同一平台内的榜单排名定价。
- 支持买入、卖出、持仓和当前会话排行榜。
- 查询行情时调用 AstrBot 当前配置的 t2i 服务绘制走势图。
- t2i 失败时自动回退为文本。
- SQLite 数据保存在 `data/plugin_data/astrbot_plugin_hot_market/`。

## 配置

安装或重载插件后，在 AstrBot WebUI 中将 `api_base_url` 改成你的 60s API 根地址：

```text
https://60s.example.com
```

不要填写 `/v2/weibo` 等具体接口路径。以 `/v2` 结尾的根地址也可以自动兼容。
群聊权限通过 WebUI 中的 `allowed_group_umos` 配置：

- 每项填写完整 UMO，而不是单独的群号。
- 在目标群发送 `/sid` 可以获取当前 UMO。
- 列表为空时拒绝所有会话，避免插件意外暴露到新群。
- 填写 `*` 表示允许所有群聊，但私聊仍然禁止。
- 未授权会话不会请求行情、创建账户或执行交易。
- 账户、资产和排行榜继续按完整 UMO 隔离。

`enabled_markets` 支持：

```text
weibo
baidu
bili
douyin
zhihu
toutiao
rednote
```

## 指令

```text
/热市 帮助
/热市 行情
/热市 行情 微博
/热市 详情 WB-XXXXXXXX
/热市 买入 WB-XXXXXXXX 300
/热市 卖出 WB-XXXXXXXX 5
/热市 卖出 WB-XXXXXXXX 全部
/热市 资产
/热市 排行
/热市 状态
/热市 刷新
```

买入指令最后一个参数表示希望投入的热币金额，插件会根据现价计算可以买到的整数股数。

## MVP 定价

同一平台榜单共有 `N` 条，热点排名为 `r`：

```text
排名强度 = ((N - r + 1) / N) ^ 1.5
目标股价 = 5 + 95 × 排名强度
```

已有股票每轮向目标价移动 40%，单轮涨跌限制为 25%。热点离榜后每轮衰减 25%，连续离榜达到配置次数后退市至 1 热币。

不同平台的原始热度值不可直接比较，因此 MVP 只使用平台内排名定价。

## 本地测试

在插件目录运行：

```powershell
python -m unittest discover -s tests -t .. -v
```
