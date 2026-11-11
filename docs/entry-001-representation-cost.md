# 論点メモ：表現設計コスト——BPL と CBR に共通する最大の死因と、現代の回答

作成：2026-11-11（プロジェクト内で提起された論点の記録。対象は `docs/entry-001-sketch.md` のエントリ001）

## 提起

BPL と CBR には、スケッチの死因診断（BPL＝計算コスト、CBR＝工学的重さ）よりも根深い、共通の死因が残っている。**人間による表現設計の泥沼**である。

- BPL を動かすには、「どんな基本パーツ（DSL）で手順を組むか」と確率モデルを人間が絶妙に設計しなければならない。
- CBR を動かすには、「何と何が似ている状況・手順なのか」という類似度のモノサシを人間が作らなければならない。特にプログラムの類似度は厄介で、1箇所のパラメータや分岐の違いで結果が真逆になることもあれば、木構造が全然違うのに全く同じ動きをする手順もある（構文と振る舞いの乖離）。
- ゆえに、コンピュータの計算コストは現代の計算資源で相殺できても、「人間が設計で頭を抱えるコスト」が融合側では2倍になり、共倒れするリスクを孕む。

これは古典的には知識工学のボトルネックとして知られる問題で、本プロジェクトの死因分類でいえば「工学的重さ」の正体に近い。エントリ001の主張は、この死因に対して何と答えるかで試される。

## 現代の回答の型：提案→検証→選別

2024年前後に揃った一群の研究は、同じ型の回答を示している。**人間が中身を設計する代わりに、機械（LLM）にコードとして提案させ、安い自動検証が選別する。** 設計の対象は「解法そのもの」から「何をどう検証するか」へ移る。

### FeatLLM（Han et al., ICML 2024）
"Large Language Models Can Automatically Engineer Features for Few-Shot Tabular Learning"（Sungwon Han, Jinsung Yoon, Sercan Ö. Arık, Tomas Pfister、arXiv:2404.09491）。
特徴量は表形式学習における「表現」そのもので、従来は人間の職人芸だった。FeatLLM は LLM を特徴エンジニアとして使い、少数の例から特徴抽出ルールをコードとして生成させる。生成された特徴は単純な下流モデル（線形回帰等）で評価され、推論時に LLM は不要。泥沼のうち「表現（特徴）の設計」を提案と検証に置き換えた直球の例。

### EoH（Liu et al., ICML 2024）
"Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model"（Fei Liu et al.、ICML 2024 Oral、PMLR 235:32201–32223）。
ヒューリスティクス（手順）の設計を、LLM と進化計算の協働に置く。ヒューリスティクスの「思考」（自然言語の着想）とコードを対にして共進化させ、適応度は問題インスタンス上での実行結果で測る。人間が設計していた発見的手順そのものが、進化の対象になった。

### FunSearch（Romera-Paredes et al., Nature 2024）
"Mathematical discoveries from program search with large language models"（Nature 625:468–475、2023年12月オンライン公開）。
凍結した LLM（Codey）が、人間が用意したプログラム骨格の中の1関数を書き換える提案を出し続け、自動評価器が幻覚と誤りを弾き、進化機構が高得点プログラムを次の提案の材料にする。cap set 問題で20年ぶりの下界改善、オンラインビンパッキングで古典的ヒューリスティクスを上回る発見的手順を得た。設計思想の核心は「LLM は賢くなくてよい。評価器が真偽の全てを判定する」。人間に残るのは問題設定・評価器・骨格であり、泥沼は消えたのではなく、**小さく見通しのよい場所（何を検証するか）に移動・圧縮された**と読むのが正確である。

### WorldCoder（Tang, Key & Ellis, NeurIPS 2024）
"WorldCoder, a Model-Based LLM Agent: Building World Models by Writing Code and Interacting with the Environment"（Hao Tang, Darren Key, Kevin Ellis、arXiv:2402.12275）。
環境の遷移と報酬を表す「世界のモデル」——表現そのもの——を、エージェントが Python プログラムとして書き、経験（リプレイバッファ）との照合で検証し、予測が外れるたびに書き直す。Ellis は DreamCoder の著者であり、BPL 系譜が「表現を人間が与える」段階から「表現を機械が書き、失敗で直す」段階へ進んだ姿と位置づけられる。ビデオゲームとロボットの計画タスクで深層 RL より最大で4桁速い学習を示した。

## エントリ001との対応

現行の系は、この型の「決定的版」になっている。提案者は LLM ではなく編集列挙（値置換→部品交換→挿入→削除のティア制修正）で、検証は実行による全例一致が担い、正しさは類似度に依存しない（類似度が外れても候補数の税金で済み、誤答にはならない）。射程は4件の研究と同じく「検証が安い領域」に限られる。

一方で、意図的に見送ったものと未解決のものが、この4件から逆照射される。

- **修正提案へのモデル併用**は、スケッチが当初想定していた（「単純な編集操作＋安いモデル」）が、現行版は決定性優先でスコープアウトした。4件の研究は併用が機能する条件（検証が安いこと）を示しており、再検討の条件は「検証側の強度が提案の暴走を上回ること」と整理できる。
- **失敗箇所の診断**：現行の修正は失敗位置を同定しない生成・検査で、修正が存在しないタスクでは全ティアの列挙代（実測88件）を払う。WorldCoder の修復は失敗した予測を手がかりにする形であり、診断の導入がこの固定費への対抗策になる。
- **失敗側の記録**：現行の履歴は成功した編集のみで、「適応の成否」の否側が残らない。類似度を「直して使えたか」から学ぶにも、修正パターンの適用条件を育てるにも、失敗側のデータが前提になる。

## 含意：設計対象は尽きない——初期環境ごと構築可能にしておく

設計しなければならないものは、DSL と類似度で終わらない。これから先も、昇格の発火条件、パターンの表現、検証用の探査入力など、「何を設計することになるか分からない」ものが現れ続ける。であれば設計原則は、各部品を手作りで完璧にすることではなく、**BPL と CBR に繋がる初期環境（種となる部品、初期事例、検証器）そのものを、提案→検証の型で構築し拡張できる形にしておくこと**になる。上記4件はその雛形である：FunSearch は骨格と評価器だけを初期環境として与え、WorldCoder は環境との相互作用から初期モデルを立ち上げ、DreamCoder の系譜は種となる基本部品からライブラリを育てる。エントリ001でも、種 DSL は「種」であることを明示し、後から足す環境部品は最終回答としてではなく、育てられる足場として導入する。

## 出典

- Han, S., Yoon, J., Arık, S. Ö., Pfister, T. "Large Language Models Can Automatically Engineer Features for Few-Shot Tabular Learning." ICML 2024. arXiv:2404.09491.
- Liu, F., Tong, X., Yuan, M., Lin, X., Luo, F., Wang, Z., Lu, Z., Zhang, Q. "Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model." ICML 2024. https://proceedings.mlr.press/v235/liu24bs.html
- Romera-Paredes, B., et al. "Mathematical discoveries from program search with large language models." Nature 625, 468–475 (2024). https://www.nature.com/articles/s41586-023-06924-6
- Tang, H., Key, D., Ellis, K. "WorldCoder, a Model-Based LLM Agent: Building World Models by Writing Code and Interacting with the Environment." NeurIPS 2024. arXiv:2402.12275. https://haotang1995.github.io/projects/worldcoder
