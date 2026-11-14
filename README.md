# 许颂毓个人主页

静态中英文双语学术主页，无构建依赖，发布于 https://notyourkev.github.io/ 。

本地预览：

```powershell
python -m http.server 4173 --directory "D:\CV_Resume\个人主页"
```

GitHub Pages 使用 `notyourkev.github.io` 仓库的 `main` 分支根目录。

## 页面维护

简介、论文、教育和实习在 `index.html` 中维护；`data-zh` / `data-en` 分别对应中英文文本。`styles.css` 负责响应式排版，教育与实习共用 `.experience` 样式。个人照片使用 `assets/portrait-life-original.jpg`，来自指定原图的完整拷贝。

## Google Scholar 引用数

`assets/scholar.json` 保存公开 Google Scholar 主页的最近成功快照。总引用数显示在简介下方，每篇论文按标题匹配引用数；未知值不展示，页面注明快照日期。

`.github/workflows/update-scholar.yml` 每天北京时间 09:17 尝试更新，也可在 GitHub Actions 中手动运行。GitHub 定时任务可能延迟；Google 限流或页面解析失败时保留上次成功数据。页面同时读取仓库中的最新快照，因此自动更新无需等待 Pages 重新构建。

手动同步与解析检查：

```powershell
python scripts/update_scholar.py --self-test
python scripts/update_scholar.py
```
