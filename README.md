# Gemini TTS 一括音声生成ツール

Google Gemini APIを使用した日本語音声合成（TTS）の一括生成ツールです。CSVファイルから複数のテキストを読み込み、高品質な音声ファイルを一括で生成します。

## 機能

- 📄 CSVファイルから複数のテキストを一括読み込み
- 🎙️ 30種類以上の話者から選択可能（男性・女性）
- 🎭 演技指示による細かな表現調整
- 📦 生成した音声ファイルをZIP形式で一括ダウンロード
- 🎵 個別ファイルのプレビューと再生

## セットアップ

### ローカル環境

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/gemini-tts.git
cd gemini-tts
```

2. 仮想環境を作成して依存関係をインストール
```bash
python -m venv .venv
source .venv/bin/activate  # Windowsの場合: .venv\Scripts\activate
pip install -r requirements.txt
```

3. 環境変数を設定
`.env`ファイルを作成し、Gemini APIキーを設定：
```
GEMINI_API_KEY=your_api_key_here
```

4. アプリを起動
```bash
streamlit run app.py
```

### Streamlit Community Cloudへのデプロイ

1. GitHubにリポジトリをプッシュ
2. [Streamlit Community Cloud](https://streamlit.io/cloud)にサインイン
3. 新しいアプリをデプロイ
4. Secrets設定で`GEMINI_API_KEY`を追加

## 使い方

### CSVファイルの形式

| 列名 | 必須 | 説明 |
|------|------|------|
| text | ✅ | 音声化するテキスト |
| voice | ❌ | 話者名（省略時はデフォルト話者を使用） |
| filename | ❌ | 出力ファイル名（省略時は自動生成） |
| instruction | ❌ | 演技指示（例：明るく元気な声で） |

### CSVサンプル

```csv
text,voice,filename,instruction
おはようございます,Zephyr,greeting,明るく元気な声で
本日のお知らせです,Kore,announcement,はっきりと聞き取りやすく
ありがとうございました,Zephyr,closing,ゆっくりと丁寧に
```

## 技術スタック

- **Frontend**: Streamlit
- **TTS API**: Google Gemini 2.5 Pro/Flash Preview
- **言語**: Python 3.11+

## ライセンス

MIT License

## 注意事項

- Gemini APIの利用にはAPIキーが必要です
- APIの利用料金が発生する場合があります
- 生成される音声ファイルの商用利用については、Google Gemini APIの利用規約をご確認ください