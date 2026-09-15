# Article audit sidecar

本文件承載內部來源、術語、claim 與缺口紀錄；不併入 Medium 正文。文章入口：[CONTEXT.md](../../CONTEXT.md)。

## Source boundary

- 程式來源：[repo snapshot 48571df4cf2b0292a0fb779b0187e80eb5036ded](https://github.com/ed3c/ops-reconciliation-copilot/tree/48571df4cf2b0292a0fb779b0187e80eb5036ded)。下列 path 與 symbol locator 均指此 snapshot；`#symbol` 是程式定位文字，不冒充 GitHub 行號錨點。
- 寫作方法：[CARD_PROTOCOL_V7_1.md](https://github.com/ed3c/ai-content-notes/blob/f3a54094cc018489bad6d2d4f5c38884322fd658/governance/CARD_PROTOCOL_V7_1.md)；只採用使用者指定 adapter 原則。
- 歷史模型報告：[committed JSON](../evidence/2026-09-15-luna-medium.json)，依報告 checkout 標註版本。[原 workflow attempt](https://github.com/ed3c/ops-reconciliation-copilot/actions/runs/34948675162/attempts/2) 與 committed JSON 是同源證據，不計兩份獨立佐證。
- SOURCE_FACT：來源直接記錄；CODE_OBSERVATION：目前可見程式；DERIVATION：由程式推導；PEDAGOGICAL_MODEL：明示簡化模型；UNKNOWN：缺必要證據。
- 來源中稱為 human confirmation / hand-labeled 的文字，不能推導真實人工參與。本文件及正文描述為測試腳本操作、固定預期值。
- 此次不呼叫付費模型、不更改應用程式或 fixtures。新的文章主例重播尚未執行。

## Evidence ledger

| evidence_id | kind | exact fact/code/result | source locator | supported claim_ids |
|---|---|---|---|---|
| E01 | CODE_OBSERVATION | parse / create：CSV 1–10000 rows；每側最多 1000000 bytes；UTF-8-sig、無重複 headers、無 malformed rows | app/main.py#parse; create | C01 |
| E02 | CODE_OBSERVATION | propose：只傳 headers；每側 ≤100 欄、每欄 ≤200 字元；max_tokens=4096、reasoning.effort=medium、socket timeout=45、response ≤65536 bytes；無應用層重試 | app/llm.py#propose; app/prompts/mapping.txt | C02 |
| E03 | CODE_OBSERVATION | validate：精確 status/mapping/question 契約；proposed 檢查實際且互異欄位；clarify 為 null mapping 與 1–500 字元問題 | app/llm.py#validate; tests/test_llm.py | C03 |
| E04 | CODE_OBSERVATION | mapping_proposal 成功只寫 mapping_proposal；set_mapping 才改 mapping 與 mapped；execute 拒絕 uploaded；reconciled 禁改 mapping | app/main.py#mapping_proposal; set_mapping; execute | C04 |
| E05 | CODE_OBSERVATION | normalize 建 transaction_id → list，保留 row；Decimal finite、abs ≤1e15 且數值可表為兩位小數；currency 為三個 ASCII 字母並 upper | app/main.py#normalize | C05 |
| E06 | CODE_OBSERVATION | reconcile 走 sorted(set(left) \| set(right))，duplicate_key → missing → currency_mismatch → amount_mismatch；delta 為 left − right | app/main.py#reconcile | C06 |
| E07 | CODE_OBSERVATION | runs(id TEXT PRIMARY KEY,data TEXT NOT NULL) 保存整份 JSON；PostgreSQL write read 使用 FOR UPDATE；模型呼叫在交易外，成功回寫前重讀並檢查 reconciled；錯誤分支另存 last_proposal_error | app/storage.py#RunStore; connect; app/main.py#mapping_proposal | C07 |
| E08 | CODE_OBSERVATION | private API 檢查 owner session；公開 static showcase 與 workspace 分開；未配置拒絕、未登入與其他身分分別處理 | app/access.py; app/google_login.py; tests/test_google_access.py; app/static/index.html | C08 |
| E09 | SOURCE_FACT | 原始歷史報告：openai/gpt-5.6-luna medium；4/4 fixed cases；1038 tokens；1184–2131 ms；checkout 78ea5882fa996cf9ef4c900bcc53cd79911b7a7a；不是本次重跑 | docs/evidence/2026-09-15-luna-medium.json; evals/cases.jsonl; evals/run.py | C09 |
| E10 | CODE_OBSERVATION | T100 fixture：100.00 USD 與 98.00 USD；expected F001 amount_mismatch delta 2.00，左右 row=2；verify_mapping 的兩次呼叫為 local fake provider，測試登入亦為 fake | tests/fixtures/left.csv; right.csv; expected.json; scripts/verify_mapping.py; scripts/verify_browser.py | C10 |
| E11 | CODE_OBSERVATION | metadata 記 model / response_model、prompt_sha、usage、elapsed_ms、live_provider；eval 對 proposed 比完整 mapping，clarify 只比 status；無成本與代表性準確率量測 | app/llm.py#propose; evals/run.py | C11 |
| E12 | DERIVATION | 複雜度須分開 rows normalization、distinct ID sorting、字串長度與 JSON 讀寫；模型服務 wall time 非本地操作計數；公式在 Stage 3 推導 | app/main.py#normalize; reconcile; app/storage.py#RunStore | C12 |
| E13 | CODE_OBSERVATION | PUT mapping 路徑不要求先有 model proposal；兩種路徑使用相同 normalize / reconcile | app/main.py#set_mapping; execute; app/static/app.js | C13 |
| E14 | CODE_OBSERVATION | runtime workflow 有 runtime 與 postgres jobs；runtime / browser / mapping 使用獨立 fixtures 與測試身分；live-eval 獨立 workflow | scripts/verify_runtime.py; scripts/verify_browser.py; .github/workflows/runtime.yml; .github/workflows/live-eval.yml | C14 |

## Term ledger

下表是凍結詞彙，不代表正文已完成 first-use definitions。後續 first-use 定義、符號與圖標籤必須逐階段核對。

| term_id | canonical English term | first zh-TW explanation | forbidden degraded variants |
|---|---|---|---|
| T01 | headers | CSV 欄位名稱 | 不得泛稱完整交易資料 |
| T02 | mapping_proposal | 模型提議及 metadata 的保存欄位 | 不得改稱已提交 mapping |
| T03 | mapping | 實際提交並驗證的欄位對應 | 不得與 proposal 混用 |
| T04 | run state | 一次工作執行的階段 | uploaded / mapped / reconciled 不改字 |
| T05 | transaction_id | 交易識別欄位 | 不得等同 run id 或 hash 位址 |
| T06 | Decimal | 程式使用的十進位數值型別 | 不得說是 LLM 算出的金額 |
| T07 | findings | 對帳差異輸出 | 不得直接稱已確認業務錯誤 |
| T08 | clarify | 要求釐清欄位的模型回應 status | 不得稱有效 mapping |
| T09 | FOR UPDATE | PostgreSQL 讀取待更新資料時使用的列鎖 | 不得稱全資料庫鎖 |
| T10 | fake provider | 本機測試用模型服務替身 | 不得稱真實模型推論 |
| T11 | live_provider | metadata 中依 endpoint 判斷的布林標記 | 標記本身不保證品質 |
| T12 | prompt_sha | prompt 的 SHA-256 | 不得稱資料集 hash |
| T13 | owner session | 經後端驗證的擁有者登入狀態 | 不得等同已實證正式 Google 登入 |
| T14 | auxiliary space | 演算法額外工作空間 | 不得包含輸出後又重複計算 |
| T15 | output space | 回傳結果佔用空間 | 不得混稱 temporary space |
| T16 | runtime witness | 可逐步對照程式的單一主例 | 未執行時不得稱精確執行 trace |

程式 identifiers（如 normalize、reconcile、uploaded、mapped、reconciled、proposed、amount_mismatch、row、delta）逐字沿用程式；Stage 1–5 首次需要時加入 term ledger，再准許出現在圖中。Complexity 符號 nL、nR、U、B、H、L、F、J 定義固定在 D10，Stage 3 推導前須補明每種操作的成本模型。

## Decision ledger

十二個 decision_id、問題、chosen path、rejected path、constraint 與 downstream sections/figures 保存在 [CONTEXT.md 的十二個決策](../../CONTEXT.md#3-十二個決策)。沒有額外讀者選項。

## Claim coverage

| claim_id | article section | figure_id or NONE | code anchor | status |
|---|---|---|---|---|
| C01 | §2、5 | 1、6 | app/main.py#parse; create | SUPPORTED；Stage 1 |
| C02 | §2、5、7、11 | 1、2、4、6 | app/llm.py#propose | SUPPORTED；Stage 1–3 |
| C03 | §3、7、8、13 | 1、2、4、6 | app/llm.py#validate | SUPPORTED；Stage 1、2、4 |
| C04 | §3、4、6、8 | 1、2、3、6 | app/main.py#mapping_proposal; set_mapping; execute | SUPPORTED；Stage 1、2、4 |
| C05 | §4、6、8、11–14 | 2、3、4、5、6 | app/main.py#normalize | SUPPORTED；Stage 1–4 |
| C06 | §6、8、11–15 | 2、3、5、6 | app/main.py#reconcile; export | SUPPORTED；Stage 2–4 |
| C07 | §7、11、12、15 | 3、5、6 | app/storage.py#RunStore; connect | SUPPORTED；Stage 2–4 |
| C08 | §7、16 | 6 | app/access.py; app/google_login.py | 程式 SUPPORTED；正式完整流程 UNKNOWN；Stage 2、4 |
| C09 | §16 | 6 | docs/evidence/2026-09-15-luna-medium.json | 歷史報告 SUPPORTED；本次 live eval NOT_RUN；Stage 4 |
| C10 | §6、13、16 | 2、6 | tests/fixtures/expected.json; scripts/verify_mapping.py | fixture SUPPORTED；文章專用 trace NOT_RUN；Stage 2、4 |
| C11 | §7、16 | 6 | app/llm.py#propose; evals/run.py | SUPPORTED；Stage 2、4 |
| C12 | §11、12 | 4、5、6 | app/main.py#normalize; reconcile; app/storage.py | DERIVATION_PENDING；Stage 3 |
| C13 | §9、10 | 4、6 | app/main.py#set_mapping; execute | SUPPORTED；Stage 3 |
| C14 | §16 | 6 | .github/workflows/runtime.yml; scripts/verify_runtime.py | 程式 SUPPORTED；本次執行另記；Stage 4 |

§1 是讀者承諾；§5、17–20 只整理既有 claims，不新增功能或實證。全部 claims 目前只完成來源與目標映射，正文 coverage / figure coverage 尚未完成。

## Open gaps

| gap_id | UNKNOWN / pending | 影響 | 解鎖條件與目標 |
|---|---|---|---|
| K01 | 正式站 Google owner + real provider 全程 browser trace | 不能說正式端到端已完成 | 在正確設定的正式站執行登入、upload、proposal、mapping、reconcile、讀回與匯出，保存去識別化證據；§16 保留 UNKNOWN 至滿足 |
| K02 | 本文單一主例的完整新 trace 尚未執行 | Stage 2 不得把推導與歷史模型拼成一條執行證據 | Stage 2 重播現有 fake-provider browser flow，保存來源版本與 result；純函式中間態若另推導則標 PEDAGOGICAL_MODEL，不冒充已 instrument 的 trace |
| K03 | 代表性準確率、模型比較、p95、貨幣成本 | 四個固定案例不可外推 | 需要獨立資料集與明確量測設計；本文章只說明目前證據限制，§16 不宣稱成果 |
| K04 | 完整操作成本推導 | Stage 0 不先發布 Big O 結論 | Stage 3 定義符號，列 normalization、set、sort、JSON 讀寫、returned references 與 serialization copies 成本 |
| K05 | 正文、six body figures、assembly | 全文不能 DONE | 依下一節逐階段完成 coverage、term integrity、code consistency 與組裝檢查 |

## Stage contract and assembly map

| stage / part_id | first heading → last heading | predecessor | successor | duplicated material removed |
|---|---|---|---|---|
| 0 | 工作標題 → Completion state | NONE | Stage 1 | NONE；尚無正文 |
| 1 / part-01 | §1 讀者承諾 → §5 決策 | Stage 0 | Stage 2 | PENDING |
| 2 / part-02 | §6 runtime → §7 internals | Stage 1 | Stage 3 | PENDING |
| 3 / part-03 | §9 alternative → §12 space | Stage 2 | Stage 4 | PENDING |
| 4 / part-04 | §8 correctness、§13 edge cases、§14 implementation → §16 verification | Stage 3 | Stage 5 | PENDING；組裝回填 §8 |
| 5 / part-05 | §17 English Q&A → §20 causal rules | Stage 4 | Stage 6.1 | PENDING |
| 6.1–6.6 | 單張完整 figure specification → 單張圖 | Stage 5 | Stage 7 | 每次一圖；不得拼貼 |
| 7 | Title → Key takeaways | Stage 6.6 | DONE 僅在全部 gate 通過後 | 屆時逐項記錄；不新增事實 |

Stage 6 每張圖需完整欄位：FIGURE_ID、TEACHING_JOB、READER_QUESTION、CANONICAL_LABELS、NODES、EDGES、SPATIAL_LAYOUT、VISUAL_HIERARCHY、STYLE、NEGATIVE_CONSTRAINTS、CAPTION、ALT_TEXT、IMAGE_GENERATION_PROMPT、CLAIM_IDS_COVERED。每個 factual label 先核對 term / claim ledger。精確關係以可核對的 diagram 表達；無正文與 ledger 支持的視覺元素不能加入。

Stage 7 將 Parts 1–5 依 CONTEXT 目錄組裝成一份 Medium canonical article；首次完整定義保留、重複內容移除但 claims 不丟失、統一 headings、插圖位置、caption / alt text。未完成圖規格與圖時不冒稱 DONE。

## Focused self-repair gates

每階段最多三次針對失敗項目修補：source fidelity、decision closure、zero-context definitions、runtime continuity、code consistency、correctness、complexity、language、anti-fragmentation、anti-duplication、figure isolation、figure grounding、stage continuity、Medium assembly。尚未到達的 gates 為 DEFERRED，不寫 PASS。

Stage 0：來源定位、12 決策、14 claims 目標、6 圖唯一工作已建立；正式全文 gates 均待後續階段。未新增虛構面試或人工審核案例。

## Current execution

本次在 Python 3.12 本機環境執行 `python scripts/verify_runtime.py`，exit code 0，輸出 `PASS: 10 runtime checks`。程式 snapshot 為上述固定 commit，僅新增文件。這只驗證既有 HTTP runtime，不包含真實模型或 Google 正式登入。

文件相對路徑、12 個決策、6 張規劃圖的結構檢查通過；尚未撰寫或生成的正文與圖片不計 coverage PASS。
