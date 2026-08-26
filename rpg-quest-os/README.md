# QUEST OS — RPG型タスク管理・スケジュール管理OS

ソーシャルゲームのRPG的なUIとルールで、自分のスタミナ（可処分な集中力）を正確に把握し、
**一度に1つだけ**物事を進めるための個人用OS。Googleカレンダーと同期し、
「資産性のある活動」と「消費されて終わる役務」を毎日切り分けて可視化する。

サーバーレス（Cloudflare）構成で運用負荷ゼロ、データの正本は追記型のテキストファイルとして
Git に積層保存する。

---

## 何が入っているか

| パス | 内容 |
|---|---|
| [`requirements/260826_REQ_RPGタスク管理OS.md`](requirements/260826_REQ_RPGタスク管理OS.md) | **要件定義書**（背景・ゲームシステム設計・機能要件FR・非機能要件NFR・API・ロードマップ・未決事項） |
| [`docs/ui/index.html`](docs/ui/index.html) | **UIモック**。ブラウザで開くとそのまま動く Phase 1 プロトタイプ（localStorage／API不要） |
| [`docs/architecture.html`](docs/architecture.html) | **アーキテクチャ図**。全体構成／正本と派生の関係／実行ボタンのシーケンス／技術選定とコスト |
| [`docs/db/QuestOS_DB設計.xlsx`](docs/db/QuestOS_DB設計.xlsx) | **DB設計スプレッドシート**（30タブ・656行） |
| [`docs/db/csv/`](docs/db/csv/) | 上記の CSV 版。Git で差分が見えるようこちらが編集元 |
| [`tools/db_spec_data.py`](tools/db_spec_data.py) | スプレッドシートの内容定義（唯一の正） |
| [`tools/build_db_spec.py`](tools/build_db_spec.py) | CSV と xlsx の生成スクリプト |
| [`vault/`](vault/) | 追記型データ正本のサンプル（イベントログ・スナップショット） |

### スプレッドシートのタブ構成

| 番台 | タブ |
|---|---|
| 00 | README / テーブル一覧 / リレーション |
| 10 | players / player_days / resource_ledger |
| 20 | quests / quest_runs / quest_templates |
| 30 | calendar_events / calendar_mappings / sync_state |
| 40 | assets / asset_events |
| 50 | skills / player_skills |
| 60 | income_records |
| 70 | runners / ai_runs / artifacts |
| 80 | event_log / snapshots / daily_reports |
| 90 | enums / balance_params / formulas / api_endpoints / screens / 要件一覧 / サンプルデータ |

---

## 中核となる考え方

### 1. AP（スタミナ）は1日の予算であって、時間ではない

`1AP ≒ 3分の通常集中作業`。負荷に応じて係数がかかる（軽作業0.6／通常1.0／深い集中1.6／消耗2.2）。
朝のチェックインで睡眠時間を入力すると、その日のAP上限が確定する。
**予定APの合計が上限を超えたら赤字として警告する** ── これが「自分の容量を把握する」の実装。

### 2. 役務は Gold を生むが、資産を1ポイントも積み上げない

| 種別 | 資産ポイント | Gold | EXP倍率 |
|---|---|---|---|
| 🏗 BUILD 建設 | ＋（大） | – | ×2.0 |
| 🌱 GROW 育成 | ＋（中） | – | ×1.5 |
| 📖 LEARN 修練 | ＋（小） | – | ×1.2 |
| ⚔️ LABOR 役務 | **0** | ＋（大） | ×0.8 |
| 🔧 MAINT 運営 | **0** | – | ×0.5 |
| 👥 RAID 会議 | 0 | – | ×0.7 |

この非対称性を **AER（資産投下率 = 資産系AP ÷ 総AP）** として毎日表示する。週次目標 40%。

### 3. 同時に出撃できるクエストは1件だけ

ホーム画面には NEXT QUEST を1件だけ大きく出し、それ以外は畳む。
出撃中は他のクエストの実行ボタンが無効化される。Durable Object で直列化して保証する。

### 4. 放置するほど重くなる

期限を超過したクエストは1日ごとに `dread` が加算され、着手時のAP消費が +5%/日 される（上限+50%）。
計画外の割り込み実行は `AMBUSH` として記録され、AP消費 ×1.2・FOCUSコンボがリセットされる。

### 5. 正本はテキストファイル。DBは捨てても作り直せる

全ての状態変化を `vault/events/YYYY-MM-DD.jsonl` に追記し、Git にコミットする。
Cloudflare D1 はそこから再生成できる読み取りモデルにすぎない。
Git のコミット履歴がそのままバージョン履歴になる。

---

## 使い方

### UIモックを見る

```shell
open docs/ui/index.html          # macOS
# または任意の静的サーバで
npx http-server docs -p 8080
```

`S` 出撃 / `D` 完了 / `A` 放棄 / `R` リセット。localStorage に保存されるので、
そのまま数日運用してゲームバランスが自分に効くかを試せる。

### DB設計スプレッドシートを再生成する

```shell
python3 tools/build_db_spec.py
```

`tools/db_spec_data.py` が唯一の正。編集後にこのコマンドを実行すると
`docs/db/csv/*.csv` と `docs/db/QuestOS_DB設計.xlsx` が更新される。外部ライブラリは不要。

---

## 構築の順序

| Phase | 構成 | 完了条件 |
|---|---|---|
| **Phase 1** | 静的HTML + localStorage のみ | 手入力で1週間、実際に運用できる |
| **Phase 2** | + Workers / D1 / Access / Cron | カレンダーから自動でクエストが並ぶ |
| **Phase 3** | + Queues / Durable Objects / R2 | 実行ボタンから Claude が動き、成果物が履歴に残る |
| **Phase 4** | 追加開発 | Asset Stock と Gold/AP が可視化される |

Phase 1 を localStorage だけで作るのは意図的な判断。
このシステムの成否は技術ではなく「ゲームルールが自分に効くかどうか」で決まるため、
効かないルールの上にインフラを積む前に、最小コストで数値を検証して調整する。

---

## 未決事項

要件定義書の [17章](requirements/260826_REQ_RPGタスク管理OS.md#17-未決事項要判断) に10件の論点と暫定回答をまとめている。
特に AP の実時間換算（暫定3分）、資産の減衰率（暫定3%/月）、週次AER目標（暫定40%）は
運用2週間後に見直す前提の数値。
