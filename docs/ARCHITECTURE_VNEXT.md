# SCS-Sim vNext 架构（设计稿 · 待批准）

> 开发约束：**仅在本机 `L:\scs-sim` 开发**，不再用云端 agent 写代码。  
> 原则：**功能只增不减**——现有 2D / API / 控制台 / 仿真内核全部保留。

## 总览

```
现有内核 + 控制台(2D)  ──保留──▶  继续可用
                 │
                 └──新增──▶  3D 地球星座渲染层 + EXE 打包 + 开源模块接入
```

## 保留（绿色，不删不降级）

| 层 | 现状 |
|----|------|
| Config / Clock | YAML、SimClock、`/control` |
| Orbit | Kepler+J2、SGP4、ECI/ECEF |
| Constellation | Walker ≤10k |
| Network | ISL/GSL/拓扑/路由 |
| Environment | 日食/大气/电源/热/辐射 |
| Compute | 节点/调度 |
| Ops / Twin | 波次、TLE、孪生对比 |
| Viz 2D | SVG 轨迹、CZML 导出、KPI |
| FastAPI UI | `/ui` 全星+单星参数调节、`/docs` |

## 新增（橙色高亮）

### A. Windows EXE 打包
- PyInstaller（或 briefcase）一键产出 `scs-sim.exe`
- 内嵌：API + 静态前端（2D+3D）+ 默认 configs
- 启动即开本地服务并拉起浏览器 / 内嵌 WebView2（二选一，优先 WebView2）
- 脚本：`scripts/build_exe.ps1`（在现有 `build_pyinstaller.ps1` 上扩展）

### B. 3D 地球星座引擎（核心新增）
- 引擎候选：**CesiumJS**（主推，已有 CZML）或 **three.js + satellite.js**
- 渲染要素：
  - 地球纹理 + 大气
  - **赤道面**、**轨道面**、**壳层/轨道高度层**
  - 卫星模型/点云（万星级可降采样显示）
  - 轨道弧 / 地面轨迹
  - ISL 光束、GSL 锥
- 数据仍走现有仿真会话（同一 `SimSession`），3D 只是视图

### C. 双视图控制台
- 在现有 `/ui` 布局中腾出主视区：
  - 左/上：保留现有 Fleet + Per-sat 控件
  - 右/中：**3D Canvas**（可全屏）
  - 底/侧：保留 2D SVG 小窗与日志
- 切换：`2D | 3D | Dual`
- 选中单星：3D 高亮 + 2D 同步

### D. GitHub / 开源模块扩大架构
| 模块 | 用途 |
|------|------|
| CesiumJS / CZML | 3D 地球与时间轴 |
| satellite.js | 浏览器侧 SGP4 预览 |
| three.js（备选） | 轻量离线 3D |
| Orekit bridge（可选后期） | 高保真，不挡 EXE 主线 |

## 模块落点（拟新增目录）

```
scs_sim/
  viz/
    control.html      # 扩展双视图（保留）
    globe3d/          # NEW：Cesium/three 前端
    layers.py         # NEW：赤道面/壳层/轨道面几何
  desktop/
    exe_entry.py     # NEW：EXE 入口
scripts/
  build_exe.ps1       # NEW/扩展
docs/
  ARCHITECTURE_VNEXT.md  # 本文
```

## 非目标（本阶段不做）
- 删减任何现有 2D/API 能力
- 云端 Cloud Agent 开发
- 必须联网才能跑的付费 Cesium Ion（可离线瓦片/自然地球底图优先）
