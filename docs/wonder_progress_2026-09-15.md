# WONDER 分层出生分子进度（2026-09-15）

本次检查恢复了仓库中已保存的 `2010-00` 批次：它原先是逗号分隔导出，已在临时目录转换为真正的制表符文件后通过字段和州 FIPS 审计。

- 完整性：`1/48` 批次通过，`47` 批次仍为 `pending`；
- 已合并行数：764 行，仅覆盖 2010 年首批 10 个州/地区；
- 严格导入器未接收不完整分子，因此正式年龄—婚姻—孩次校准仍保持关闭；
- 没有对缺失批次插值、复制或使用 aggregate ASFR 代替分层出生数。

审计命令：

```bash
PYTHONPATH=src python3 scripts/check_wonder_completeness.py \
  data/observed/us_2021/wonder_batches_2010_2017.json \
  --input-dir /tmp/wonder_tsv
PYTHONPATH=src python3 scripts/collect_wonder_batches.py \
  data/observed/us_2021/wonder_batches_2010_2017.json \
  --input-dir /tmp/wonder_tsv \
  --output /tmp/wonder_births_2010_2017.csv
```

下一批手动导出后只需按 `<year>-<batch>.tsv` 命名放入 `/tmp/wonder_tsv/`，再运行上述两条命令。只有达到 `48/48` 且每批州 FIPS、字段和总量审计通过，才允许进入正式 hazard 校准。
