# RPGタスク管理OS「QUEST OS」要件定義書

> Version: 0.1 (初版・要件詰め用ドラフト)
> 対象読者: 本人（単一プレイヤー）＋実装を担当する Claude Code
> 関連: [アーキテクチャ図](../docs/architecture.html) / [UIモック](../docs/ui/index.html) / [DB設計スプレッドシート](../docs/db/QuestOS_DB設計.xlsx)

---

## 1. 概要

### 1.1 目的

日々のタスク・スケジュールを「ソーシャルゲームのRPG」のメタファーで管理し、
**自分の可処分リソース（スタミナ）を数値で正確に把握したうえで、一度に1つだけ物事を進める**ための個人用OSを構築する。

### 1.2 背景（As-Is の課題）

| # | 課題 | 具体的な症状 |
|---|---|---|
| P1 | 自分への指示が甘くなる | 「あとでやる」で無限に後ろ倒しになる |
| P2 | スケジュールが厳密に運用できない | カレンダーに入れた予定が実行されず形骸化する |
| P3 | 自分の容量を把握していない | 1日にこなせない量を予定に入れて破綻する |
| P4 | 役務（労働）と資産形成の区別がない | 気づくと資産性のない作業だけで1日が終わる |
| P5 | 積み上がっているのか分からない | 成果がストックされている実感が持てない |
| P6 | 何にフォーカスしているか曖昧 | 並行タスクが多く、どれも中途半端になる |

### 1.3 狙い（To-Be）

| # | 対応する課題 | 打ち手 |
|---|---|---|
| S1 | P1 / P2 | ゲームルールという**外形的な制約**を自分に課す。完了/放棄が数値（EXP・FOCUS・dread）に即反映される |
| S2 | P3 | **AP（スタミナ）** を導入し、1日の予定AP合計が上限を超えたら赤字警告を出す |
| S3 | P4 / P5 | すべてのクエストを**資産性軸**で分類し、`AER`（資産投下率）と `Asset Stock` を毎日可視化 |
| S4 | P6 | ホーム画面には **NEXT QUEST を1件だけ**大きく出す。それ以外は畳む |
| S5 | P5 | 成果物・状態を **追記型（append-only）のファイル履歴**として積層保存し、いつでもブラウザから参照できる |

### 1.4 基本コンセプト

```
現実世界              ゲーム世界
─────────────────────────────────────────
可処分な集中力       →  AP（スタミナ）
体力・気力           →  VIT
連続で崩さない集中   →  FOCUS（コンボ）
タスク               →  クエスト
Googleカレンダー予定 →  出撃予定（討伐依頼）
受託・事務作業       →  役務クエスト（Gold は稼げるが積み上がらない）
プロダクト・コンテンツ→ 資産クエスト（Asset Stock が積み上がる）
売上・報酬           →  Gold
出来上がった資産     →  宝物庫（Assets）
できること           →  ステータス／スキルツリー
Claude の実行        →  召喚（AI Runner）
```

---

## 2. スコープ

### 2.1 スコープ内（本要件の対象）

- 単一ユーザー（本人）向けのタスク／スケジュール管理
- Google カレンダーとの同期（読み取り＋実績書き戻し）
- RPG的リソース管理（AP / VIT / FOCUS / EXP / LV / Gold / Asset Stock）
- ブラウザで動作する静的HTMLインターフェース
- Cloudflare 上のサーバーレスAPI（Workers / D1 / KV / R2 / Queues）
- クエストの「実行ボタン」から Claude API を呼び出す AI Runner
- ローカル（Claude Code）でのファイル生成と、追記型のバージョン履歴保存
- 収益（役務収入／資産収入）の記録と、AP効率の可視化

### 2.2 スコープ外（今回はやらない）

- マルチユーザー／チーム機能、共有・権限管理
- ネイティブモバイルアプリ（PWAでの閲覧までは対象）
- AWS / GCP 等のマネージドサーバー運用（**明示的に排除する**）
- 会計ソフト・請求書発行との連携（収益は手入力またはCSV取込）
- リアルタイム性の高い通知（プッシュ通知は Phase 3 以降）
- 他社カレンダー（Outlook 等）との同期

### 2.3 前提・制約

| # | 制約 |
|---|---|
| C1 | 運用負荷ゼロを最優先。常時起動サーバー・コンテナは持たない |
| C2 | データの正本は**ローカルのテキストファイル（JSONL/MD）**。DBは再構築可能な派生物とする |
| C3 | 静的HTML＋クライアントJSで閲覧が完結すること（APIが落ちても過去は読める） |
| C4 | 単一ユーザー前提。認証は Cloudflare Access に委譲し、アプリ側で認証機構を作らない |
| C5 | Claude API の呼び出しは従量課金。1実行あたりのトークン上限とコスト上限を設ける |
| C6 | Google Calendar API の無料枠（1,000,000 queries/day）内に収まる同期頻度とする |

---

## 3. 用語定義

| 用語 | 英語/識別子 | 定義 |
|---|---|---|
| AP | `ap` | スタミナ。1日の可処分な集中リソース。1AP ≒ 3分の通常集中作業 |
| VIT | `vit` | 気力・体力。会議や消耗タスクで減り、睡眠と休息で回復する |
| FOCUS | `focus` | 集中コンボ段数（0〜5）。連続完了で加算、中断で0 |
| EXP / LV | `exp` / `level` | 経験値とレベル。APmax とスキル解放に影響 |
| Gold | `gold` | 実際に入金された／確定した金額（円） |
| クエスト | `quest` | 実行単位のタスク。カレンダー予定または手動で生成 |
| 資産性 | `asset_score` | そのクエストが将来にわたって価値を生むか（0〜100） |
| 役務 | `LABOR` | 消費されて終わる作業。Gold は入るが Asset Stock は増えない |
| Asset Stock | `asset_stock` | 積み上がった資産ポイントの総和（減衰あり） |
| AER | `aer` | Asset Efficiency Ratio。期間内の資産系AP消費 ÷ 総AP消費 |
| dread | `dread` | 先延ばし累積値。放置日数に応じて着手コスト（AP）が増える |
| AMBUSH | `is_ambush` | 未計画の割り込み実行フラグ |
| Runner | `runner` | クエストに紐づく Claude 実行定義（プロンプト＋入出力） |
| Vault | `vault/` | 追記型のローカル正本ディレクトリ |

---

## 4. 利用シーン（1日の流れ）

```
06:30  起床チェックイン
       → 睡眠時間を入力 → AP/VIT が回復し「今日のAP予算」が確定
       → Googleカレンダーが同期され、予定が「出撃予定」としてボードに並ぶ
       → 予定AP合計 137 / 上限 120 → 【AP赤字 -17】警告
       → 「MAINT系2件（計18AP）をBACKLOGへ送る」提案を受け入れて 119/120 に調整

09:00  HOMEを開く → NEXT QUEST が1件だけ表示される
       「🏗 プロダクトのLP改稿（BUILD / 32AP / 60分）」
       → [出撃] を押す → タイマー開始、他のクエストはグレーアウト

09:15  [⚡実行] を押す → Claude が LP 改稿ドラフトを生成
       → 成果物が vault/artifacts/ に保存され、画面に差分表示

10:05  [完了] → AP -32 / EXP +77（32 × 2.0 BUILD × 1.0 FOCUS0 × 1.2 時間厳守）/ FOCUS 0→1
       → Asset「自社LP」の asset_points +12、durability 72→85
       → Googleカレンダーの「実績ログ」に実績イベントが書き戻される

13:00  未計画の電話対応が発生 → [AMBUSH] として記録
       → AP -14（×1.2）/ FOCUS 3→0 / VIT -8

18:00  デイリーレポート
       → 消化 88AP / AER 46%（目標40%達成）/ Gold +45,000（役務）
       → Claude による講評と、明日のクエスト提案
       → 1日分のイベントが vault/events/2026-08-26.jsonl に確定追記され、
         git commit → Cloudflare Pages へ反映
```

---

## 5. ゲームシステム設計

### 5.1 リソース

#### 5.1.1 AP（スタミナ）

- **最大値**: `APmax = min(200, 100 + floor(LV / 5) × 10)`
- **回復**: 原則として1日1回のロールオーバー時に全回復（＝1日の予算）
  - `回復量 = APmax × min(1.0, 睡眠時間 / 7.0)` … 睡眠不足はそのまま上限低下として反映する
- **日中回復**: `REST` クエストのみ `+10〜30AP`。**1日あたり合計 +40AP を上限**とする
- **消費**: `AP消費 = ceil(見積分 / 3 × 負荷係数 × dread係数 × ambush係数 × 消耗デバフ)`

| 負荷 | `load` | 係数 | 例 |
|---|---|---|---|
| 軽作業 | `LIGHT` | 0.6 | メール返信、経費入力 |
| 通常 | `NORMAL` | 1.0 | 資料作成、実装 |
| 深い集中 | `DEEP` | 1.6 | 設計、執筆、難所の実装 |
| 消耗 | `DRAIN` | 2.2 | 対人交渉、不確実性の高い折衝 |

- `dread係数 = 1 + 0.05 × dread`（上限 1.5）
- `ambush係数 = 1.2`（未計画実行時）／ 通常 1.0
- `消耗デバフ = 1.3`（VIT < 30 のとき）／ 通常 1.0

#### 5.1.2 VIT（気力）

- 最大 100
- 回復: `VIT += 睡眠時間 × 12`（上限100）、`REST` クエストで `+5〜20`
- 消費: `RAID`（会議）で `参加人数 × 2 + 分/10`、`DRAIN` 負荷で `分/6`、24時以降の作業で `分/5`
- **デバフ**:
  - `VIT < 30` → 「消耗」: AP消費 ×1.3、FOCUS上限 3
  - `VIT = 0` → 「行動不能」: `REST` 以外の [出撃] ボタンを無効化する

#### 5.1.3 FOCUS（集中コンボ）

- 0〜5段
- `+1`: クエストを中断せず完了したとき
- `0にリセット`: 放棄・AMBUSH実行・完了せずに日跨ぎ
- 効果: `EXP倍率 = 1.0 + 0.1 × FOCUS`（最大1.5）

### 5.2 経験値・レベル・ステータス

- `基礎EXP = 実消費AP`
- `獲得EXP = 基礎EXP × 種別倍率 × FOCUS倍率 × 時間厳守ボーナス`
  - 時間厳守ボーナス: 予定開始の ±15分以内に着手 `×1.2` / 予定日を超過して着手 `×0.8`
- `次のレベルまで: NEXT(LV) = round(100 × LV ^ 1.35)`（LV1=100 / LV5=871 / LV12=2,863 / LV20=6,244）

**ステータス6系統**（獲得EXPの30%が `stat_tags` に振り分けられる）

| ステータス | 意味 | 上がるクエスト例 |
|---|---|---|
| STR 推進 | 実行して終わらせる力 | 締切のある納品、山場の突破 |
| INT 設計 | 構造化・企画・戦略 | 設計、要件定義、事業計画 |
| DEX 実装 | 手数と速度 | コーディング、制作、編集 |
| CHA 交渉 | 対人・営業・発信 | 商談、登壇、採用 |
| LUK 露出 | 偶発的な機会創出 | 発信、投稿、コミュニティ |
| VIT 継続 | 続ける力・体調管理 | 運動、睡眠、ルーティン維持 |

### 5.3 クエスト種別（資産性による分類）

| 種別 | 記号 | 意味 | 資産性 | EXP倍率 | Gold | Asset Stock |
|---|---|---|---|---|---|---|
| `BUILD` | 🏗 | 資産を新規に作る | 高 (70-100) | ×2.0 | – | ＋（大） |
| `GROW` | 🌱 | 既存資産を伸ばす／保守 | 中高 (50-80) | ×1.5 | – | ＋（中）・durability回復 |
| `LEARN` | 📖 | 自分自身への投資 | 中 (40-70) | ×1.2 | – | ＋（小・スキル） |
| `LABOR` | ⚔️ | 受託・役務。消費されて終わる | 低 (0-20) | ×0.8 | ＋（大） | – |
| `MAINT` | 🔧 | 事務・運営・維持 | ゼロ (0) | ×0.5 | – | – |
| `RAID` | 👥 | 会議・打合せ | 可変 | ×0.7 | – | – |
| `REST` | 💤 | 休息・回復 | – | ×0 | – | AP/VIT回復 |

> **設計意図**: `LABOR` は Gold を生むが Asset Stock を1ポイントも増やさない。
> この非対称性を毎日ダッシュボードで見せることが、本システムの最大の目的。

### 5.4 Gold と資産ストック

#### Gold（実収益）
- `active_income`: 役務由来（LABOR に紐づく）
- `passive_income`: 資産由来（Asset に紐づく／MRR・広告・印税など）
- **Gold/AP 効率** = 期間内 Gold ÷ 期間内消費AP … 「1APいくらで売っているか」

#### Asset Stock（資産ポイント）
- `asset_points += 消費AP × 種別係数`（BUILD 1.0 / GROW 0.6 / LEARN 0.4）
- **減衰**: 日次ロールオーバー時に `asset_points ×= (1 - decay_rate/30)`
  - `decay_rate` 既定 3%/月。最終更新から90日超で 8%/月に加速
- **durability（耐久値 0-100）**: 放置で `-1/日`。`GROW` 実行で回復。
  - `durability = 0` → 「休眠資産」表示となり passive_income の計上を停止する

#### AER（資産投下率）
```
AER = (BUILD + GROW + LEARN の消費AP) ÷ 総消費AP
```
- 日次・週次・月次で表示。**週次目標 AER ≥ 40%** を既定とする
- AER が2週連続で 25% 未満 → 「役務過多」アラートを出す

### 5.5 ペナルティ

| 名称 | 発生条件 | 効果 |
|---|---|---|
| dread（先延ばし） | 期限を超過して未着手 | 1日ごとに `dread +1`。着手時 AP消費 +5%/dread（上限+50%） |
| AMBUSH（強襲） | 計画外クエストを実行 | AP消費 ×1.2、FOCUS を 0 にリセット |
| AP赤字 | 当日予定AP合計 > APmax | ボードに赤字バナー。超過分の BACKLOG 送りを提案 |
| 消耗 | VIT < 30 | AP消費 ×1.3、FOCUS上限 3 |
| 行動不能 | VIT = 0 | REST 以外の出撃を禁止 |

### 5.6 バランス調整の方針

すべての係数は `91_balance_params` タブ（→ DBの `balance_params` テーブル）で外出しし、
コード変更なしに調整できること。初期値は上記の通りとし、運用2週間後に見直す。

---

## 6. 機能要件

> ID規約: `FR-<機能群>-<連番>` / 優先度: `MUST` = Phase1必須, `SHOULD` = Phase2, `COULD` = Phase3

### 6.1 F1: ダッシュボード（拠点）

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F1-01 | AP / VIT / FOCUS / LV / EXP / Gold を常時ヘッダに表示する | MUST |
| FR-F1-02 | **NEXT QUEST を1件だけ**画面中央に大きく表示する。次点以降は折り畳む | MUST |
| FR-F1-03 | NEXT QUEST の選定は「予定時刻 > dread > 資産性 > AP適合」の順で自動決定する | MUST |
| FR-F1-04 | 当日の「予定AP合計 / APmax」をゲージ表示し、超過時は赤字バナーを出す | MUST |
| FR-F1-05 | 当日および直近7日の AER を表示する | MUST |
| FR-F1-06 | 現在アクティブなクエストがある間、他クエストの[出撃]を無効化する（並行禁止） | MUST |
| FR-F1-07 | ステータス6系統をレーダーチャートで表示する | SHOULD |
| FR-F1-08 | 現在有効なデバフ（消耗／行動不能／AP赤字）をバッジ表示する | MUST |

### 6.2 F2: クエスト管理

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F2-01 | クエストを手動作成できる（タイトル・種別・負荷・見積分・期限・stat_tags・関連Asset） | MUST |
| FR-F2-02 | 作成時に AP見積を自動計算し、確定前に表示する | MUST |
| FR-F2-03 | 状態遷移: `BACKLOG → PLANNED → ACTIVE → DONE / ABANDONED / EXPIRED` | MUST |
| FR-F2-04 | [出撃]（start）でタイマーを開始し、AP を仮予約する | MUST |
| FR-F2-05 | [完了]（complete）で実測時間から AP を確定消費し、EXP/Gold/AssetPoint を付与する | MUST |
| FR-F2-06 | [放棄]（abandon）で FOCUS を0にし、dread を+1する | MUST |
| FR-F2-07 | 計画外クエストの即時実行を `AMBUSH` として記録できる | MUST |
| FR-F2-08 | 定型クエスト（デイリー/ウィークリー）をテンプレートから自動生成する | SHOULD |
| FR-F2-09 | クエストを BACKLOG へ送る／期日を繰り越すと dread が加算される | MUST |
| FR-F2-10 | 種別・資産性・期限・関連Assetでフィルタ／並べ替えができる | SHOULD |
| FR-F2-11 | サブクエスト（親子関係）を1階層まで持てる | COULD |

### 6.3 F3: Googleカレンダー同期

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F3-01 | Google Calendar から指定期間（既定: 前7日〜先30日）のイベントを取得する | MUST |
| FR-F3-02 | Cron Trigger により15分間隔で自動同期する（差分同期: `syncToken` を利用） | MUST |
| FR-F3-03 | イベント → クエストのマッピングルールを設定できる | MUST |
| FR-F3-04 | マッピングは ①タイトル接頭辞（`[B]`=BUILD 等） ②カレンダーID ③colorId の優先順で解決する | MUST |
| FR-F3-05 | マッピング不能なイベントは種別 `UNSORTED` として受信箱に入れ、手動仕分けを促す | MUST |
| FR-F3-06 | イベントの所要時間から見積分を自動設定する（負荷は種別の既定値） | MUST |
| FR-F3-07 | 参加者数が2名以上のイベントは `RAID` として扱う | SHOULD |
| FR-F3-08 | クエスト完了時、専用カレンダー「QuestOS 実績ログ」へ実績イベントを書き戻す | SHOULD |
| FR-F3-09 | 同期の競合（カレンダー側で削除/変更）は「カレンダー優先」で解決する。ただし `DONE` 済みクエストは保持する | MUST |
| FR-F3-10 | 終日イベントは AP計算対象外とし、`context` として扱う（旅行・休暇など） | SHOULD |
| FR-F3-11 | 手動同期ボタンを備える | MUST |

### 6.4 F4: AI Runner（実行ボタン）

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F4-01 | クエスト詳細に [⚡実行] ボタンを置き、押下で Claude API を呼び出す | MUST |
| FR-F4-02 | Runner定義（system prompt / user template / 入力参照 / 出力形式 / モデル / max_tokens）をクエストに紐づけられる | MUST |
| FR-F4-03 | 実行は非同期（Queues）とし、進捗を SSE でストリーミング表示する | MUST |
| FR-F4-04 | 出力は成果物として `vault/artifacts/<run_id>/` と R2 に保存する | MUST |
| FR-F4-05 | 実行ログ（入力トークン/出力トークン/概算コスト/所要時間/モデル）を記録する | MUST |
| FR-F4-06 | 1実行あたりのトークン上限、および日次コスト上限を設定し、超過時は実行を拒否する | MUST |
| FR-F4-07 | 同一クエストで複数回実行した場合、成果物をバージョンとして積層保存する | MUST |
| FR-F4-08 | 成果物の採否（採用／破棄）を記録し、採用時のみ Asset に反映する | SHOULD |
| FR-F4-09 | 失敗時は最大2回まで指数バックオフで再試行する | SHOULD |
| FR-F4-10 | Claude Code のローカルスキルからも同じ Runner 定義を実行できる | SHOULD |

### 6.5 F5: 資産管理（宝物庫）

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F5-01 | Asset を登録できる（名称・種類・説明・関連URL・収益モデル） | MUST |
| FR-F5-02 | asset_points と durability を表示し、日次で減衰させる | MUST |
| FR-F5-03 | Asset に紐づくクエスト履歴と、投下した累計APを表示する | MUST |
| FR-F5-04 | Asset ごとの passive_income と「投下AP あたりの回収額」を表示する | SHOULD |
| FR-F5-05 | durability が閾値（既定30）を下回った Asset を「要メンテ」として提示する | SHOULD |
| FR-F5-06 | 資産種別: `PRODUCT` / `CONTENT` / `SYSTEM` / `AUDIENCE` / `SKILL` / `RELATION` | MUST |

### 6.6 F6: 収益管理

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F6-01 | 収益レコードを登録できる（日付・金額・区分 active/passive・取引先・関連Asset/Quest） | MUST |
| FR-F6-02 | 月次の active / passive の内訳を積み上げグラフで表示する | MUST |
| FR-F6-03 | Gold/AP 効率を期間別に表示する | MUST |
| FR-F6-04 | MRR（継続収益）を別枠で集計する | SHOULD |
| FR-F6-05 | CSV 取込に対応する | COULD |

### 6.7 F7: レポート・振り返り

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F7-01 | 日次レポート（消化AP / AER / 完了・放棄数 / Gold / FOCUS最高値）を自動生成する | MUST |
| FR-F7-02 | Claude による日次講評と、翌日のクエスト提案を生成する | SHOULD |
| FR-F7-03 | 週次レポート（AER推移 / ステータス成長 / Asset Stock推移）を生成する | SHOULD |
| FR-F7-04 | 「役務過多」「AP赤字が3日連続」等のアラートを提示する | SHOULD |

### 6.8 F8: データ管理・バージョン履歴

| ID | 要件 | 優先度 |
|---|---|---|
| FR-F8-01 | 全ての状態変化を **追記型イベント**として `vault/events/YYYY-MM-DD.jsonl` に記録する | MUST |
| FR-F8-02 | イベントログを再生すれば任意時点の状態を再構築できること（イベントソーシング） | MUST |
| FR-F8-03 | 日次で状態スナップショット `vault/snapshots/YYYY-MM-DD.json` を出力する | MUST |
| FR-F8-04 | Vault を Git 管理し、日次で commit / push する | MUST |
| FR-F8-05 | 過去のスナップショットをブラウザから閲覧・比較（diff）できる | SHOULD |
| FR-F8-06 | API が停止していても、静的化された過去データはブラウザで閲覧できる | MUST |
| FR-F8-07 | 全データを JSON / CSV でエクスポートできる | SHOULD |

---

## 7. 非機能要件

| ID | 分類 | 要件 |
|---|---|---|
| NFR-01 | 性能 | ダッシュボード初期表示 1.5秒以内（Cloudflare エッジキャッシュ利用） |
| NFR-02 | 性能 | クエスト操作系API（start/complete）のレスポンス 300ms 以内 |
| NFR-03 | 可用性 | API 停止時も静的サイトで過去データの閲覧が可能（グレースフルデグレード） |
| NFR-04 | 運用性 | サーバー・コンテナの常時起動なし。運用作業は「git push」のみ |
| NFR-05 | 保守性 | ゲームバランス係数はすべて DB の `balance_params` に外出しし、再デプロイ不要 |
| NFR-06 | 移植性 | データ正本はプレーンテキスト（JSONL/MD/CSV）。DBロックインを避ける |
| NFR-07 | セキュリティ | Cloudflare Access（Google IdP）で全経路を保護。アプリ独自の認証は実装しない |
| NFR-08 | セキュリティ | API キー・OAuth リフレッシュトークンは Workers Secrets / KV（AES-GCM暗号化）に保存し、クライアントに配布しない |
| NFR-09 | コスト | 月額ランニング 3,000円以内（Cloudflare $5 + Claude API 従量）。日次コスト上限を設定 |
| NFR-10 | 可搬性 | スマートフォンのブラウザで閲覧・操作できる（レスポンシブ、375px〜） |
| NFR-11 | 監査性 | すべての状態変化がイベントログから追跡可能であること |
| NFR-12 | 障害復旧 | D1 を全損しても Vault のイベントログから完全復元できること（RPO=1日、RTO=1時間） |
| NFR-13 | 可用性 | Google Calendar API 障害時も、直近同期済みのローカルキャッシュで動作継続 |
| NFR-14 | アクセシビリティ | 主要操作はキーボードのみで完結（`n`=次のクエスト、`s`=出撃、`d`=完了） |

---

## 8. アーキテクチャ

> 図: [docs/architecture.html](../docs/architecture.html)

### 8.1 全体構成

```
┌─ ローカル（Claude Code） ───────────────────────────────┐
│  skill: quest-os                                        │
│  vault/                                                 │
│   ├ events/YYYY-MM-DD.jsonl   ← 正本（append-only）      │
│   ├ snapshots/YYYY-MM-DD.json ← 日次スナップショット      │
│   └ artifacts/<run_id>/       ← AI成果物                 │
│  site/                        ← 静的化された閲覧用HTML    │
└──────────────┬──────────────────────────────────────────┘
               │ git push
               ▼
┌─ GitHub ────────────────────────────────────────────────┐
│  リポジトリ = バージョン履歴そのもの                      │
│  GitHub Actions: build → deploy                          │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─ Cloudflare ────────────────────────────────────────────┐
│  Pages        静的HTML/JS（閲覧は常に可能）               │
│  Access       Google IdP による認証（全経路の前段）       │
│  Workers      Hono による API（/api/*）                   │
│   ├ D1        読み取りモデル（SQLite）                    │
│   ├ KV        設定・OAuthトークン・セッション             │
│   ├ R2        成果物・スナップショットのオブジェクト保存   │
│   ├ Queues    AI Runner の非同期実行                      │
│   ├ Durable Objects  実行状態・SSE配信・AP整合性ロック     │
│   └ Cron      15分毎のカレンダー同期／日次ロールオーバー   │
└──────┬─────────────────────────┬────────────────────────┘
       │                         │
       ▼                         ▼
 Google Calendar API      Anthropic Messages API
```

### 8.2 設計判断とその理由

| 判断 | 理由 |
|---|---|
| 正本を JSONL イベントログにする | 「ソースファイルを重ねてバージョン履歴として保存する」という要望を、Git と自然に噛み合う形で実現するため。DB は捨てても復元できる |
| D1 はプロジェクション（派生物） | 集計・検索の速度が欲しいが、正本にはしない。スキーマ変更時は再生成するだけで済む |
| Cloudflare Pages ＋ Workers | 常時起動サーバーが不要で運用負荷ゼロ。静的部分とAPIを同一ドメインで配信でき、CORS 設計が不要 |
| Cloudflare Access に認証を委譲 | 単一ユーザーにパスワード管理機構を自作するのは過剰。IdP に寄せる |
| AI Runner を Queues + Durable Objects で非同期化 | Workers の CPU時間制限を回避しつつ、長時間実行の進捗を SSE で返すため |
| AP の整合性を Durable Object で守る | 「同時に1つしか出撃できない」という中核ルールを、単一の直列化ポイントで保証する |

### 8.3 データフロー（実行ボタン押下時）

```
ブラウザ  ──POST /api/quests/:id/run──▶  Worker
                                          │ ①run レコード作成（status=QUEUED）
                                          │ ②Queue へ enqueue
                                          ▼
ブラウザ  ◀──run_id──────────────────  Worker
   │
   └──GET /api/runs/:id/stream (SSE)──▶  Durable Object
                                          ▲ 進捗をpush
                                          │
                              Queue Consumer Worker
                                 │ ③Runner定義を D1 から取得
                                 │ ④Anthropic Messages API 呼び出し（stream）
                                 │ ⑤トークン/コストを記録
                                 │ ⑥成果物を R2 に保存
                                 │ ⑦イベントを event_log に追記
                                 ▼
                          日次ロールオーバー(Cron)
                                 │ ⑧vault/events/*.jsonl を書き出し
                                 │ ⑨GitHub へ commit / push
                                 ▼
                          Pages 再デプロイ（静的履歴が更新される）
```

---

## 9. 画面一覧

| ID | 画面 | 主な内容 | 優先度 |
|---|---|---|---|
| SC-01 | HOME（拠点） | ステータスバー、NEXT QUEST（1件）、AP収支ゲージ、AER、デバフ | MUST |
| SC-02 | QUEST BOARD | 当日／週のクエスト一覧、フィルタ、受信箱（UNSORTED） | MUST |
| SC-03 | QUEST DETAIL | 詳細、Runner設定、[出撃]/[完了]/[放棄]、成果物バージョン | MUST |
| SC-04 | CALENDAR | 週表示、AP見積オーバーレイ、AP赤字の可視化 | SHOULD |
| SC-05 | ASSETS（宝物庫） | 資産一覧、durability、投下AP、回収額 | MUST |
| SC-06 | STATUS | レーダーチャート、LV/EXP、スキルツリー | SHOULD |
| SC-07 | LEDGER（収支） | Gold推移、active/passive内訳、Gold/AP | SHOULD |
| SC-08 | REPORT | 日次/週次レポート、AI講評 | SHOULD |
| SC-09 | HISTORY（書庫） | スナップショット一覧、diff表示 | COULD |
| SC-10 | SETTINGS | カレンダーマッピング、バランス係数、コスト上限 | MUST |

---

## 10. API 一覧（Cloudflare Workers）

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/state` | 現在のプレイヤー状態（AP/VIT/FOCUS/LV/Gold/デバフ） |
| GET | `/api/quests` | クエスト一覧（`?date=` `?status=` `?type=`） |
| POST | `/api/quests` | クエスト作成 |
| PATCH | `/api/quests/:id` | クエスト更新 |
| POST | `/api/quests/:id/start` | 出撃（AP仮予約・排他ロック取得） |
| POST | `/api/quests/:id/complete` | 完了（AP確定・EXP/Gold/AssetPoint付与） |
| POST | `/api/quests/:id/abandon` | 放棄（FOCUSリセット・dread加算） |
| POST | `/api/quests/:id/defer` | 繰り越し（dread加算） |
| POST | `/api/quests/:id/run` | AI Runner 起動 → `run_id` |
| GET | `/api/runs/:id` | 実行状態・結果 |
| GET | `/api/runs/:id/stream` | 実行進捗（SSE） |
| POST | `/api/runs/:id/accept` | 成果物の採用／破棄 |
| POST | `/api/rest` | 休息（AP/VIT回復） |
| POST | `/api/checkin` | 起床チェックイン（睡眠時間入力・日次ロールオーバー） |
| POST | `/api/sync/calendar` | カレンダー手動同期 |
| GET | `/api/assets` / POST / PATCH | 資産管理 |
| GET | `/api/income` / POST | 収益管理 |
| GET | `/api/report/daily` | 日次レポート（`?date=`） |
| GET | `/api/report/weekly` | 週次レポート |
| GET | `/api/snapshots` | スナップショット一覧 |
| POST | `/api/snapshot` | スナップショット手動作成 |
| GET | `/api/settings` / PUT | 設定・バランス係数 |

---

## 11. 外部連携

### 11.1 Google Calendar

| 項目 | 内容 |
|---|---|
| 認証 | OAuth 2.0（`calendar.readonly` + `calendar.events`）。refresh token を KV に暗号化保存 |
| 取得API | `events.list`（`syncToken` による差分同期。410 応答時はフル再同期） |
| 書き戻し | `events.insert`（専用カレンダー「QuestOS 実績ログ」へ） |
| 同期頻度 | Cron 15分間隔 ＋ 手動 |
| 冪等性 | `google_event_id` をユニークキーとして upsert |

**イベント → クエスト マッピング規則（優先度順）**

1. タイトル接頭辞: `[B]`→BUILD / `[G]`→GROW / `[L]`→LABOR / `[M]`→MAINT / `[R]`→RAID / `[S]`→LEARN / `[Z]`→REST
2. カレンダーID: 設定で「このカレンダーは全部 LABOR」等を指定
3. colorId: 設定で色→種別を指定
4. 参加者2名以上 → `RAID`
5. いずれにも該当しない → `UNSORTED`（受信箱へ）

### 11.2 Anthropic Messages API

| 項目 | 内容 |
|---|---|
| 既定モデル | `claude-sonnet-5`（日常実行） / `claude-opus-5`（設計・企画系 Runner） |
| 呼び出し | Workers から `stream: true` で呼び、Durable Object 経由で SSE 中継 |
| 上限 | 1実行 `max_tokens` 既定 8,000。日次コスト上限 既定 300円 |
| 記録 | `ai_runs` に model / input_tokens / output_tokens / cost_jpy / latency_ms を保存 |
| 失敗時 | 429/5xx は最大2回まで指数バックオフ（2s, 8s）。それ以外は即失敗 |

---

## 12. データモデル概要

詳細は [docs/db/QuestOS_DB設計.xlsx](../docs/db/QuestOS_DB設計.xlsx)（CSV版: `docs/db/csv/`）を参照。

### 12.1 テーブル一覧

| # | テーブル | 役割 |
|---|---|---|
| 1 | `players` | プレイヤー（本人）の恒常プロフィール、LV、累計EXP |
| 2 | `player_days` | 日次のAP/VIT/FOCUS・睡眠・デバフの状態 |
| 3 | `resource_ledger` | AP/VIT/EXP/Gold/AssetPoint の全増減台帳 |
| 4 | `quests` | クエスト本体 |
| 5 | `quest_runs` | 出撃〜完了の実行記録（1クエストに複数回ありうる） |
| 6 | `quest_templates` | 定型クエスト（デイリー／ウィークリー） |
| 7 | `calendar_events` | Googleカレンダー同期データ |
| 8 | `calendar_mappings` | イベント→種別のマッピング規則 |
| 9 | `sync_state` | 同期カーソル（syncToken 等） |
| 10 | `assets` | 資産 |
| 11 | `asset_events` | 資産ポイントの増減・減衰・耐久変動 |
| 12 | `skills` | スキル定義（ツリー） |
| 13 | `player_skills` | 習得状況 |
| 14 | `income_records` | 収益記録 |
| 15 | `runners` | AI Runner 定義 |
| 16 | `ai_runs` | Claude 実行ログ |
| 17 | `artifacts` | 成果物（バージョン付き） |
| 18 | `event_log` | イベントソーシング正本（append-only） |
| 19 | `snapshots` | 日次スナップショット |
| 20 | `balance_params` | ゲームバランス係数 |
| 21 | `daily_reports` | 日次レポート |

### 12.2 主要リレーション

```
players 1─n player_days
players 1─n quests
quests  1─n quest_runs
quests  n─1 calendar_events   （カレンダー由来の場合）
quests  n─1 assets            （資産に紐づく場合）
quests  n─1 runners
quest_runs 1─n ai_runs
ai_runs 1─n artifacts
assets  1─n asset_events
assets  1─n income_records
すべての状態変化 → event_log（append-only）
```

---

## 13. セキュリティ・権限

| # | 要件 |
|---|---|
| SEC-01 | Cloudflare Access（Google IdP）で `*.pages.dev` および `/api/*` を保護する |
| SEC-02 | Worker は `Cf-Access-Jwt-Assertion` を検証し、許可メールアドレス以外を拒否する |
| SEC-03 | Anthropic API キーは Workers Secrets に格納し、クライアントに一切出さない |
| SEC-04 | Google OAuth refresh token は KV に AES-GCM で暗号化して保存する（鍵は Secrets） |
| SEC-05 | Vault（Git リポジトリ）は Private とする。成果物に機密が含まれうるため |
| SEC-06 | R2 バケットは公開しない。閲覧は Worker 経由の署名付きURLとする |
| SEC-07 | AI Runner に渡す入力は、クエスト・資産・成果物に限定する（無制限のファイル読み取りをさせない） |
| SEC-08 | 日次コスト上限を超えた場合、AI Runner を自動停止する |

---

## 14. 運用・コスト

| 項目 | 見積 |
|---|---|
| Cloudflare Workers Paid | $5 / 月 |
| Cloudflare D1 / KV / R2 / Queues | 個人利用規模では無料枠内 |
| Cloudflare Pages | 無料 |
| Anthropic API | 1日5〜10実行想定で 300〜1,500円 / 月 |
| GitHub | 無料（Private リポジトリ） |
| **合計** | **概ね 1,000〜2,500円 / 月** |

**運用手順**
- 日次: 起床チェックイン（アプリ上で30秒）
- 日次: Cron が自動でスナップショット出力 → GitHub push（無人）
- 週次: 週次レポートを確認し、バランス係数を必要に応じて調整
- 障害時: `wrangler d1 execute` で Vault のイベントログを再生し D1 を再構築

---

## 15. ロードマップ

| Phase | 期間目安 | 内容 | 完了条件 |
|---|---|---|---|
| **Phase 0** | 本ドキュメント | 要件定義・DB設計・UIモック・アーキ図 | 本人レビュー完了 |
| **Phase 1** | 2週間 | 静的HTML＋localStorage で単体動作。AP/クエスト/完了/AER が回る | 手入力で1週間運用できる |
| **Phase 2** | 2週間 | Cloudflare Workers + D1 へ移行。Googleカレンダー同期 | カレンダーから自動でクエストが並ぶ |
| **Phase 3** | 2週間 | AI Runner（実行ボタン）、成果物保存、日次レポート | 実行ボタンから Claude が動き成果物が残る |
| **Phase 4** | 随時 | 資産管理・収益管理・スキルツリー・履歴diff | Asset Stock と Gold/AP が可視化される |

> **Phase 1 を localStorage で完結させる**のは意図的な判断。
> まずゲームルールが自分に効くかを最小コストで検証し、効かなければルールを直す。

---

## 16. 受け入れ基準（Phase 1）

| # | 基準 |
|---|---|
| AC-01 | 起床チェックインで睡眠時間を入力すると、AP/VIT が規定式どおりに回復する |
| AC-02 | クエストを作成すると AP見積が自動計算される |
| AC-03 | 当日の予定AP合計が APmax を超えると赤字バナーが表示される |
| AC-04 | HOME には NEXT QUEST が常に1件だけ表示される |
| AC-05 | 出撃中は他クエストの[出撃]ボタンが押せない |
| AC-06 | 完了すると AP が減り、種別倍率に応じた EXP が入り、FOCUS が+1される |
| AC-07 | 放棄すると FOCUS が0になり、dread が+1される |
| AC-08 | 当日と直近7日の AER が表示される |
| AC-09 | VIT が30未満のとき「消耗」バッジが出て AP消費が1.3倍になる |
| AC-10 | 1日の終わりに日次レポートが生成され、JSONとして書き出せる |

---

## 17. 未決事項（要判断）

| # | 論点 | 選択肢 | 暫定 |
|---|---|---|---|
| Q1 | 1AP の実時間換算 | 3分 / 5分 / 可変 | **3分**（100AP=5時間の集中）。運用して調整 |
| Q2 | AP の日中自然回復 | あり（時間経過） / なし（1日1回） | **なし**。「1日の予算」という性質を強く出すため |
| Q3 | 並行実行の禁止 | 完全禁止 / 2枠まで | **完全禁止**（「1つずつ進める」という目的に直結） |
| Q4 | 資産の減衰 | あり / なし | **あり**（3%/月）。放置資産を見える化するため |
| Q5 | Gold の定義 | 入金ベース / 発生ベース | **発生ベース**（確定した売上）。入金は別途 |
| Q6 | カレンダー書き戻し | する / しない | **する**（別カレンダーへ）。実績の痕跡を残すため |
| Q7 | Phase 1 のデータ保存先 | localStorage / D1 いきなり | **localStorage**（検証優先） |
| Q8 | 未計画作業の扱い | 記録しない / AMBUSH として記録 | **AMBUSH**。計画外を可視化しないと改善できない |
| Q9 | スキルツリーの導入時期 | Phase 1 / Phase 4 | **Phase 4**（コアループの検証が先） |
| Q10 | 通知（催促） | しない / メール / LINE | **Phase 3以降**。まず自発運用で回るかを見る |

---

## 18. 関連ドキュメント

- [アーキテクチャ図（HTML）](../docs/architecture.html)
- [UIモック（HTML）](../docs/ui/index.html)
- [DB設計スプレッドシート](../docs/db/QuestOS_DB設計.xlsx) ／ [CSV版](../docs/db/csv/)
- [プロジェクトREADME](../README.md)

---

作成日: 260826
更新日: 260826
