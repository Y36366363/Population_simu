# 当前阻碍与解决路径（2026-09-09）

## 唯一实质阻碍

正式年龄—婚姻—孩次 calibration 缺少完整的州—年出生分子：WONDER manifest 当前为
`success=1, pending=47`，并且 2018—2021 test 分子也没有独立文件。这不是代码错误，
而是外部数据尚未导出。

## 已解决的部分

- 静态 Pages 和本地 Python API 可用；
- ACS calibration/test 暴露面板和总 ASFR 面板可用；
- artifact 版本、test 隔离、模型比较和结果校验脚本已完成；
- NCHS public-use fallback 的 URL 已确认存在；当前环境的 Python DNS 受限，未保存下载文件。

## 最短解决路径

优先级 A：继续按 manifest 手动导出剩余 WONDER TSV，逐批运行完整性和总量审计。

优先级 B：下载 NCHS 年度 public-use ZIP（2018—2021，约数百 MB/年），依据官方
fixed-width codebook 编写解析器，再按母亲居住州、年龄、婚姻和孩次聚合。该路径不需要
48 次 WONDER 查询，但需要保存 codebook、下载校验和 recode 说明。

在任一路径完成前，不运行正式 hazard 校准，也不把部分分子接入网页。当前可继续的是
总 ASFR 预测比较、机制消融、网页和本地 API 回归测试。
