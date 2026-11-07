# 琶洲 A 赛道公开展示站

静态站点入口为 `index.html`，包含赛题任务、公开真机数据来源、数据质检、GPU 基线、mock 仿真结果、报告和三分钟 MP4。

## 媒体

- `downloads/pazhou_a_showcase_3min.mp4`：1280×720、10 fps、普通话旁白，精确 180 秒。
- `assets/pazhou_a_showcase_3min_web.mp4`：640×360 网页播放压缩版。
- `assets/demo.gif`、`assets/keyframes.png`、`assets/timeline.png`：本地 mock 仿真可视化。

## 内容边界

页面不包含约 2.86 GB 原始 ALOHA 视频数据，只链接回数据来源；评分细则、官方 SDK、Isaac Sim 场景和真机 A 赛道结果均未提供/未验证。所有页面指标均注明来源和验证范围。

## 部署

公开站点由仓库根目录的 `.github/workflows/pages.yml` 部署到 GitHub Pages。配置为 GitHub Actions 发布源；推送 `main` 分支的 `site/**` 更新会触发重新部署。根目录 `wrangler.jsonc` 另保留 Cloudflare Workers Static Assets 配置。
