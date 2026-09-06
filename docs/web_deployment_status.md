# 网页部署状态与决策（2026-09-06）

## 决策

保留当前 `docs/` 纯静态网页作为项目说明和机制演示入口，不等待全部实证数据完成；
但暂不把年龄—婚姻—孩次出生分子、正式历史回放或因果反事实接入网页交互。这样网页
可以稳定展示已冻结的机制，而不会把未完成校准的数据误读为现实预测。

## 当前检查

- `docs/index.html`、`docs/app.js`、`docs/styles.css` 和 `docs/.nojekyll` 均存在；
- 页面资源使用相对路径，适合 GitHub Pages 的项目子路径；
- 仓库当前没有 `.github/workflows`，因此没有自动 Pages 构建工作流；
- Pages 应在 GitHub 仓库 Settings → Pages 中选择 `Deploy from a branch`、`main`、`/docs`；
- 本地验证应使用浏览器打开静态页面，或在允许绑定端口的环境运行 `python3 -m http.server --directory docs`。

## 统一建设的前置条件

只有在以下条件满足后，才把网页升级为“实证结果面板”：

1. 2010—2017 WONDER 48 批次全部通过审计，或完成已记录的替代出生分子路径；
2. 2018—2021 untouched test 出生分子单独保存；
3. ACS 暴露、出生结果和州—年键形成不可变分析面板；
4. 四类模型、rolling-origin、CRPS、区间覆盖率和配对置信区间全部生成可复现 artifact；
5. 年龄分层、家庭机制消融与 cohort-component 对账通过；
6. 网页只读取版本化 JSON/CSV 结果，不在浏览器端重新估计参数。

## 目前允许的网页内容

- 机制示意和固定随机种子的交互沙盘；
- Python 年度结果的静态或版本化时间线；
- 模型验证状态、数据覆盖和冻结项说明；
- 明确标记为 smoke test、预测比较或机制解释的结果。

