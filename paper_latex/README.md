# paper_latex

这是基于 `paper_draft/` 与 `experiment_new/final_submission/` 生成的中文论文 LaTeX 工程。

## 目录结构

- `main.tex`：论文主文件。
- `sections/`：摘要、引言、相关工作、方法、实验和结论。
- `figures/`：投稿用 6 张最终图片。
- `tables/`：投稿用 5 个最终表格。
- `references.bib`：参考文献数据库。
- `compile_check.md`：编译检查结果。

## 编译方式

建议使用 XeLaTeX：

```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

## 注意事项

- 本工程未加入真实机器人实验或 pending 数据。
- 实验表格和图片均来自 `experiment_new/final_submission/`。
- 作者、单位和基金等信息仍保留空白位置，投稿前需补充。
