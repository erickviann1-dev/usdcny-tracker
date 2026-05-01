# USD/CNY Macro-Policy Divergence Tracker

> 一个量化"美中政策压力 vs 市场定价"博弈的三层宏观追踪器，2 年期利差焦点。
>
> **For Cursor / future contributors:** before editing, read in this order →
> `README.md` (this file) → `CHANGELOG.md` (what's been done & why) →
> `REFERENCE_STUDY.md` (design rationale, what NOT to revert).
> Before destructive edits run `python tools/snapshot.py <tag>` to archive state.

## 项目本质

测量并可视化以下三个层次的压力：

1. **名义敞口套利（Layer 1）** — 借低利率 CNY 投高利率 USD 的毛收益
2. **定价偏离（Layer 2）** — 实际汇率 vs 多变量模型（Spread + DXY）的残差
3. **政策意图（Layer 3）** — PBOC 中间价（去除 DXY 隔夜噪音后）vs 市场预期的偏差

最终合成一个 **0-100 的 Composite Pressure Score**，回答："PBOC 这条红线还能守多久？"

---

## 项目结构

```
usdcny-tracker/
├── build.py              ★ 一键入口：抓数据 + 算分析 → 生成 web/data.json
├── data_fetcher.py       数据层（akshare + yfinance + Eastmoney + FRED 多级兜底）
├── analytics.py          三层量化引擎（核心逻辑都在这）
├── config.py             阈值、权重、配色
├── requirements.txt
├── app.py                Streamlit 版本（参考，主交付物是 web/）
├── charts.py             Streamlit 版图表（同上）
└── web/                  ★ 静态网页（最终交付物，双语 EN/中文）
    ├── index.html        页面骨架 + CSS + data-i18n 标记
    ├── dashboard.js      渲染逻辑 + i18n 引擎 + 150+ 条中英对照词典
    └── data.json         当前数据快照
```

---

## 如何运行

```bash
# 在 usdcny-tracker 目录下
pip install -r requirements.txt

# 1. 刷数据（任何一次改了 data_fetcher.py 或 analytics.py 之后都重跑）
python build.py
# 输出：web/data.json，并打印关键指标

# 2. 起本地服务器
python -m http.server 8765 --directory web
# 浏览器打开 http://localhost:8765
```

`build.py` 之外的所有 .py 文件都是被它 import 的，**不要单独运行**。

网站右上角有 **EN / 中文** 切换按钮，语言偏好自动保存到 `localStorage`。

---

## 三层架构详解

### Layer 1 — Unhedged Raw Carry（名义敞口套利）

**位置**：`analytics.py: calc_carry()`

```python
raw_carry          = US_2Y - CN_2Y                  # 单位 %
carry_ma{20,60,120}= rolling means
carry_pct_rank     = percentile vs trailing 252d
carry_pct_rank_2y  = percentile vs trailing 504d
```

**诚实声明**：免费 API 拿不到 USD/CNY swap points / NDF forward 报价，所以**没**真正算 hedged carry。dashboard 上明确标注 "Unhedged Raw Carry / 名义敞口套利"。当前 dashboard 上的 carry 值是**毛差**，不是对冲后净收益。

### Layer 2 — Multivariate OLS Mispricing

**位置**：`analytics.py: calc_mispricing()`

**A. CIP Fair Value 路径**

```
F_CIP = S_base × [(1+r_CN)² / (1+r_US)²] / [(1+r_CN_base)² / (1+r_US_base)²]
cip_deviation = usdcny_actual - F_CIP
```
2 期幂次假设 2 年期复利。利率从 % 转小数（÷100）已在代码内处理。

**B. 多变量回归（核心）**

```
USD/CNY_t = α + β₁ · Spread_t + β₂ · DXY_t + ε_t       (rolling 252d, np.linalg.lstsq)
```

- **β₁ (spread)**: 控制 DXY 后利差对 spot 的边际影响
  - ⚠️ 当前 β₁ 为负值 (-0.033)，原因是与 DXY 的强多重共线性。**这不是 bug**，而是洞察：在当前 252 天窗口中，DXY 是主导驱动因素，"纯利差扩大（不伴随美元走强）不足以击穿央行防线"。Dashboard 已加注释说明。
- **β₂ (DXY)**: DXY 每涨 1pt → CNY 弱 ~0.05-0.10 CNY
- **R²**: 模型解释力
- **residual**: 利差 + DXY 都解释不了的部分 = 中国本土因素 / 政策干预

同时保留单变量残差 `reg_residual_uni` 用于对照展示。

### Layer 3 — DXY-Adjusted PBOC Fixing Bias

**位置**：`analytics.py: calc_fixing_bias()`

**核心逻辑**：北京 4:30PM 收盘 → 次日 9:15AM 中间价之间隔了一整个 NY 交易时段。如果 DXY 隔夜走强，次日中间价机械上抬本来就该发生 — 必须先剔除这个噪音。

```python
# 滚动估计 α (CNY 对 DXY 的回报敏感度)
alpha_cny_dxy = cov(cny_ret, dxy_ret) / var(dxy_ret)   # 252d window

# 中和 NY 隔夜美元波动
expected_fix    = market_anchor × (1 + α × dxy_overnight_return)
fixing_bias     = pboc_fix - expected_fix              # ← 干净信号
fixing_bias_raw = pboc_fix - market_anchor             # ← 对照：未调整版

defense_intensity = -bias_20d_mean.rolling(20).mean()  # 取负号让"防御高"=数值大
```

**符号约定**：
- `fixing_bias < 0` → PBOC 把中间价定得比 DXY 调整后预期更强 → **defending CNY**
- `fixing_bias > 0` → PBOC 把中间价定得比预期更弱 → **allowing weakness**

### Composite Score

```
composite = W_CARRY × carry_pct_rank
          + W_MISPR × mispricing_score      (CIP dev + reg residual 双分位)
          + W_FIXING × policy_score          (fixing_bias 分位)
```
默认权重 0.35 / 0.30 / 0.35。每个分量已是 0-100 分位数。

---

## 数据源 → 字段映射

| 字段 | 来源 | 当前覆盖率 |
|---|---|---|
| `cn_2y` | akshare `bond_zh_us_rate()` 第 1 数值列 | 99% ✅ |
| `us_2y` | akshare `bond_zh_us_rate()` 第 7 数值列 | 100% ✅ |
| `usdcny` | yfinance (`USDCNY=X`/`CNY=X`) → akshare `forex_hist_em` 多 symbol → Eastmoney K 线 → FRED `DEXCHUS` | 100% ✅ |
| `usdcnh` | yfinance (`USDCNH=X`/`CNH=X`) → akshare `forex_hist_em` 多 symbol → Eastmoney K 线 | **0% ❌** (管道就绪，待数据源上线) |
| `pboc_fix` | akshare `currency_boc_sina()` "美元"列 | 100% ✅ |
| `dxy` | yfinance `DX-Y.NYB` → akshare → **FRED CSV `DTWEXBGS`** | 100% ✅ |

### 数据完整性策略（v3.0 起）

> **No fake data is better than fake data.**

- `usdcny`：若所有市场源均失败，**不再**用 `pboc_fix` 填充。宁可让 Layer 3 标记"降低置信度"，也不让 `fixing_bias` 退化为纯 DXY 隔夜反向指标。
- `usdcnh`：尚未有可用免费源。Layer 3 在无 CNH 时回退为用 CNY prev close 做 anchor（不如 CNH 准确，但不是 fix→fix 自循环）。
- Dashboard 在 spot 缺失时显示 **Data Integrity Notice**（中英双语）。

---

## 待办优先级（Cursor 接手后）

### ✅ 已完成

1. ~~**修 USD/CNY onshore spot 数据源**~~ → v3.0 done
   - 多级兜底：yfinance (多 ticker) → akshare `forex_hist_em` (5 种 symbol) → Eastmoney K 线 API (3 种 secid) → FRED `DEXCHUS`
   - 加 `_is_valid_usdcny_series()` 有效性校验（点数 + 5.0–9.0 价格区间）
   - 彻底移除 `pboc_fix → usdcny` 回填

2. ~~**加 USD/CNH 离岸数据管道**~~ → v3.0 done (管道就绪，待源上线)
   - `fetch_usdcnh_offshore_spot()`：akshare 多 symbol + Eastmoney K 线
   - 当前免费 API 均无 CNH 历史数据，覆盖率仍为 0%

### 🟠 中优先级 — 模型升级

3. **DXY 切换到真 ICE DXY**
   - 当前用 FRED `DTWEXBGS`（broad TWI，值 ~118），不是 ICE DXY（值 ~104）
   - 篮子不同：FRED 用贸易加权 26 国，ICE 用 EUR(57.6%)/JPY/GBP/CAD/SEK/CHF
   - 相关性 ~0.95，但解读时需注意
   - 试 `akshare.index_us_stock_sina(symbol=".DXY")`

4. **多元回归加更多 covariate**
   - 当前 R²=46%，DXY 没吸完所有噪音
   - 候选：VIX（风险溢价）、铜价/油价（商品冲击）、中美 PMI 差（增长预期）
   - 注意 multicollinearity（spread 和 DXY 已经高度相关）

5. **Hedged carry 真实化**
   - 加 NDF / FX swap point 数据源（这是付费门槛最高的）
   - 或允许 dashboard 上手动输入当前 1Y NDF point，前端实时计算

### 🟢 低优先级 — 工程改进

6. `data_fetcher.py: fetch_bond_yields()` 用列位置（第 1、第 7）拿数据 — akshare schema 改了就会断。换成更稳健的中文列名匹配（处理好 GBK 编码问题）。

7. CIP 公式当前用 2 期幂次（假设 2 年复利）。如要换 day-count 约定（连续复利 / 单利 / 实际天数），改 `analytics.py: calc_mispricing()` 第 95-101 行。

8. 加单元测试：用 synthetic data 测试三层公式的方向性（避免符号搞反）。

---

## 关键约定（修改前请确认）

| 约定 | 当前实现 | 含义 |
|---|---|---|
| `raw_carry > 0` | US_2Y > CN_2Y | 借 CNY 投 USD 有毛收益 |
| `β₁ (spread)` 当前为负 | -0.033（多重共线性） | 控制 DXY 后利差边际影响被吸收，详见 β₁ 注释 |
| `β₂ (DXY)` 应为正 | 当前 0.0738 ✅ | DXY 涨 → USD/CNY 升 → CNY 弱 |
| `α (CNY/DXY)` 教科书范围 | 当前 0.271 | 略低于 0.3–0.5 区间，但合理 |
| `fixing_bias < 0` | 中间价比预期强 | PBOC 在防御 CNY |
| `defense_intensity` | -bias_20d_mean | 取负让"防御高"=数值大 |
| Composite score 高 | 三层分量都高 | CNY 贬值压力大 |

如需翻转任一符号，对应改 `analytics.py` 的相应函数 + `dashboard.js` 里 `renderKPIs`/`renderAlerts` 的颜色阈值（`bull` / `bear`）。

---

## 当前实测数据快照（2026-05-01）

| 指标 | 值 | 状态 |
|---|---|---|
| 复合压力分数 | **58 / 100** | 🟡 Elevated |
| US 2Y / CN 2Y | 3.88% / 1.26% | — |
| Raw Carry | **2.62%** | 🔴 超 2.5% 警戒线 |
| USD/CNY (市场源) | 6.84 | ✅ 非 fix 代替 |
| USD/CNH | N/A | ❌ 无可用源 |
| PBOC Fix | 6.82 | ✅ |
| DXY (FRED TWI) | 118.73 | — |
| β₁ (Spread) / β₂ (DXY) / R² | -0.033 / 0.074 / 45.7% | β₁ 负值 = DXY 共线性 |
| α (CNY/DXY) | 0.271 | ✅ 合理区间 |
| Fixing Bias (DXY-adj) | -0.01 | ✅ 不再退化为 0 |

---

## 已知缺陷清单

| # | 问题 | 位置 | 严重度 |
|---|---|---|---|
| 1 | ~~USD/CNY spot 用 PBOC fix 代替~~ → **已修复 v3.0** | data_fetcher | ✅ 解决 |
| 2 | CNH 数据完全缺失（管道就绪，待源上线） | data_fetcher | 🔴 高 |
| 3 | DXY 用 FRED TWI 不是 ICE DXY | data_fetcher | 🟠 中 |
| 4 | 多元 OLS 仅含 2 个 covariate，R² 偏低 | analytics Layer 2.B | 🟠 中 |
| 5 | Hedged carry 没用真 swap points | analytics Layer 1 | 🟠 中 |
| 6 | bond_zh_us_rate 用列位置（schema 改就断） | data_fetcher | 🟡 低 |
| 7 | CIP 复利 day-count 约定可能需要调整 | analytics Layer 2.A | 🟡 低 |

---

## License / 用途

仅供研究使用，非投资建议。

数据来源：akshare（中债收益率、PBOC 中间价）、Eastmoney（FX K 线）、FRED（美元贸易加权指数、DEXCHUS）、yfinance（FX，当前网络下 SSL 不可用）。
