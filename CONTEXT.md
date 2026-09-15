# 讓 LLM 提議欄位，讓程式負責對帳：Ops Reconciliation Copilot 的 AI Engineering 實作

副標題：從 header-only mapping proposal 到 Decimal findings，理解輸出契約、執行邊界、持久化與評估證據。

> Stage 0 — Directory and Decision Freeze。這是文章規劃，不是已完成的技術長文。正文與六張圖將依階段補齊。
>
> [回 README](README.md) · [公開展示](https://ops-reconciliation-copilot.vercel.app/) · [來源與覆蓋紀錄](docs/article-runtime/audit.md)

## 1. 工作標題與範圍

**讓 LLM 提議欄位，讓程式負責對帳：Ops Reconciliation Copilot 的 AI Engineering 實作**

以 Python / FastAPI 的現有程式為解釋對象。來源固定於 [48571df4cf2b0292a0fb779b0187e80eb5036ded](https://github.com/ed3c/ops-reconciliation-copilot/tree/48571df4cf2b0292a0fb779b0187e80eb5036ded)；歷史模型報告使用自己的 checkout，不視為目前版本的重新執行。

採用使用者提供的 Zero-Context Technical Article + Six-Figure Compiler v1.0：zh-TW、exact English technical terms、evidence-first、staged-lossless、mechanism-first。參考 [ai-content-notes v7.1](https://github.com/ed3c/ai-content-notes/blob/f3a54094cc018489bad6d2d4f5c38884322fd658/governance/CARD_PROTOCOL_V7_1.md) 的來源邊界、未知標記、跨階段保存與 task-value-first 原則。該文件作為方法資料，不是本 repo 的功能證據或程式 runtime prompt。

文章不虛構面試紀錄、人工審核案例、企業採用或正式站驗證。教學 Q&A 只壓縮已解釋的機制。README 保持已實作功能與證據入口。

## 2. Medium 文章目錄

標題與副標題如上；以下是正文閱讀順序：

1. 讀者承諾：讀完能從輸入重建哪些行為？
2. 問題：兩份 CSV 的輸入、findings 輸出與限制
3. Decision 1：模型提議為何不能直接成為執行依據？
4. Decision 2：sources、mapping_proposal、mapping 與 run state 如何分工？
5. 完整決策表：每個選擇由哪項限制導出？
6. Runtime witness：T100 的 100.00 USD 與 98.00 USD 如何變成差額？
7. Runtime internals：欄位驗證、交易分界、列鎖與身分檢查
8. Correctness spine：前置條件、狀態轉移與結果保證
9. 唯一替代方案：直接指定 mapping
10. Decision boundary：何時需要 LLM，何時直接選欄？
11. Time complexity：從解析、查找與排序逐步計算
12. Space complexity：暫存索引、來源副本與輸出分開計算
13. Edge cases：歧義、無效回應、重複 ID 與不可解析金額
14. Implementation：依目前版本串起模型與確定性計算
15. Code-to-runtime mapping：函式、API、目錄與資料的對照
16. Verification：契約測試、fake provider 與歷史真實模型評估各證明什麼？
17. Concise English Q&A：用機制回答問題（教學，非面試紀錄）
18. Input-first memory pack：從輸入重建設計
19. Zero-context master map：從限制走到結果與證據
20. Key takeaways：可由程式驗證的因果規則

## 3. 十二個決策

| ID | Decision | 選擇 | 未採用路徑 | 決定條件／未解事項 | 下游 |
|---|---|---|---|---|---|
| D1 | Source boundary | 固定 repo commit，程式與原始報告分開引用；v7.1 僅作寫作方法來源 | 不以 README 敘述或測試字串推導真實使用 | 來源須可定位；正式站完整流程仍為 UNKNOWN | 全部 |
| D2 | Reader task | 讓零背景工程師重建欄位提議、確定性計算與驗證 | 不擴張到 repo 未實作的模型訓練、RAG 或企業採用 | 只處理 AI Engineer 強相關部分 | §1–20 |
| D3 | Central question | 如何用 LLM 辨識欄位，又讓對帳結果可重算、可驗證？ | 不以工具清單代替問題 | LLM 輸出需要獨立驗證與執行邊界 | §1–5；圖1 |
| D4 | Invariant | mapping_proposal 不直接改寫 mapping 或觸發 reconcile；結果由已提交 mapping 與 sources 決定 | 不將 JSON 合法等同語意正確 | 模型提議沒有執行權限；reconciled 後不能改 mapping | §3、8；圖1、3 |
| D5 | Constraint leverage | CSV 每側 1–10000 列、最多 1000000 bytes；模型每側 ≤100 headers、每欄名 ≤200 字元；只送 headers | 不將交易列交給模型推算差額 | 傳輸限制與兩位小數金額驗證已存在程式 | §2、5、11–13；圖1、5 |
| D6 | Primary representation | run JSON 分開保存 sources / mapping_proposal / mapping / findings；normalize 建立 transaction_id → list 的索引 | 不把 proposal 當 mapping，不以單值覆寫重複 ID | 保留原始 row 位置與重複鍵，支援獨立提交 mapping | §4、6–8；圖2、3 |
| D7 | Runtime witness | 沿用 fixtures：左 txn_ref=T100、amount=100.00、currency=USD；右 reference_id=T100、paid=98.00、ccy=USD | 不把歷史 aliases 模型回應拼成正式站完整 trace | 主例走成功路徑；fake provider 首次失敗／再次成功須標明；其他錯誤以負案例補充 | §6、7、13、16；圖2 |
| D8 | Correctness spine | 有效來源及 mapping → normalize → 固定分類優先序 → findings；分開驗證模型契約與計算 | 不宣稱模型語意必然正確，也不把測試通過當形式化證明 | duplicate_key 優先於 missing、currency_mismatch、amount_mismatch | §8、13–16；圖3、6 |
| D9 | Alternative | 選現有直接指定 mapping 路徑；與 LLM 路徑共用驗證、normalize、reconcile | 不新增未實作的第二套演算法或虛構 benchmark | 已知欄位對應可省模型請求；歧義欄名需澄清 | §9、10；圖4 |
| D10 | Complexity model | 定義 nL/nR 列數、U 唯一 ID 數、B 來源 bytes、H 欄名字元數、L 最長 ID、F findings 數、J 序列化 run 大小；逐操作推導 | 不把含 sorted 的程式寫成純線性，也不把模型延遲視為常數時間保證 | 查找平均模型、字串成本、JSON 整份讀寫、輸出空間須分開；推導留到 Stage 3 | §11、12；圖4、5 |
| D11 | Section and figure mapping | 依因果順序列 20 節，6 張 body figures 各有唯一工作；Stage 6.1–6.6 逐張生成 | 不產出拼貼、提前生成圖或用圖加入新事實 | 正文先凍結；caption、alt text、prompt、claim 對照齊全才生成；cover 本輪不規劃 | §1–20；圖1–6 |
| D12 | Completion state | Stage 0 可進 Stage 1；全文、圖片與最終 assembly 均未完成 | 不宣告文章 DONE 或正式站端到端完成 | UNKNOWN 保留解鎖條件；下一階段僅撰寫 Problem → Invariant → Representation | 全部 |

## 4. Logical runtime directory

以下使用 `article-runtime/` 的邏輯角色，不代表每個目錄或檔案已存在。本次實際新增本文件、[audit.md](docs/article-runtime/audit.md) 與 [run-state.json](docs/article-runtime/run-state.json)，並修改 README 引用。

| 邏輯目錄 | 角色 | 目前實體對應／狀態 |
|---|---|---|
| 00-input/ | task.md、sources/、constraints.yaml | 本文件決策表與 audit.md 的來源範圍；來源留在原始路徑 |
| 10-audit/ | evidence-ledger.md、term-ledger.md、decision-ledger.md、claim-coverage.md、open-gaps.md | audit.md 分節承載；decision-ledger 在本文件 |
| 20-cards/ | narrative.md、concept.md、detail-runtime.md、strategy-alternative.md、verification.md、knowledge-gaps.md | 尚未建立；後續按需要使用 N/C/D/T/S/P/V/K，沒有矛盾不建立 X |
| 30-article/ | outline.md、part-01.md 至 part-06.md、medium-canonical.md | outline 在本文件；正文尚未建立；Parts 1–5 對應 Stage 1–5，part-06 保留不用 |
| 40-figures/ | figure-manifest.md、figure-01.md 至 figure-06.md、cover.md | manifest 在下表；圖規格、圖片與 cover 均未建立 |
| 50-state/ | run-state.json、coverage-report.md、assembly-map.md | run-state.json 已建立；coverage 在 audit.md；assembly 尚未開始 |

## 5. Article / figure coverage map

| Figure | 唯一工作 | 文章範圍 | 必須呈現的內容 | Claims | 正文／生成階段 |
|---|---|---|---|---|---|
| 1 | Problem and decision map | §2–5 | 輸入類別、限制、提議權限與所選 representation | C01–C04 | Stage 1 / 6.1 |
| 2 | End-to-end runtime data flow | §6 | 單一 T100 主例的 sources → proposal → mapping → findings → 匯出；明示 fake provider | C02–C06、C10 | Stage 2 / 6.2 |
| 3 | Data model / system internals | §4、7、8 | run 身分、transaction_id、可修改邊界、索引、資料庫交易與列鎖 | C04–C07 | Stage 2 / 6.3 |
| 4 | Alternative and cost mechanism | §9、10 | LLM 提議 vs 直接 mapping；多出的傳輸與驗證成本、共用計算 | C02–C05、C12、C13 | Stage 3 / 6.4 |
| 5 | Complexity derivation | §11、12 | normalize、sorted union、findings、JSON 讀寫的時間與空間推導 | C05–C07、C12 | Stage 3 / 6.5 |
| 6 | Zero-context master map | §19、20 | 僅用前文概念串起限制、決策、執行、成本與分層驗證 | C01–C14 | Stage 5 / 6.6 |

圖 1 不教 runtime internals；圖 2 不比較替代方案；圖 3 不重述全文；圖 4 不加入無關實作；圖 5 不用裝飾口號；只有圖 6 可放全局關係，且不能加入新概念。私人 API 的身分檢查與模型證據限制在正文 §7、16 解釋，圖 6 只引用已定義內容。

每張圖在 Stage 6 保留獨立 caption、alt text、standalone image-generation prompt、canonical labels 與 claim 對照；正文 Stage 1–5 僅放對應 placeholder。圖 1–6 的 caption 與規格尚未撰寫，圖片尚未生成。封面是可選的獨立產物，本輪不規劃。

Stage 4 先撰寫 implementation 與 correctness；Stage 7 組裝時，將 correctness 放回目錄 §8，維持閱讀因果順序。§16 的驗證範圍與 implementation 一起在 Stage 4 撰寫。書寫順序與最終閱讀順序分開記錄。

## 6. Completion state

**READY_FOR_PART_1**。整體狀態為 CONTINUE。

下一階段精確限定為 **Stage 1 — Problem → Invariant → Representation**：撰寫開場、輸入輸出與限制、invariant、representation、讀者版決策，僅插入 Figure 1 的 placeholder、caption、alt text。收到「繼續」才開始。

待解項目不阻塞 Stage 1：正式站 Google owner + 真實模型完整瀏覽器流程仍為 UNKNOWN；新文章的完整主例 trace 尚未重新執行；代表性準確率、p95、貨幣成本沒有證據。詳細解鎖條件保留在 audit.md，未完成分支不寫成已驗證結論。DONE 只留給 Stage 7 完成文章、六圖、術語、程式一致性與 assembly 檢查之後。
