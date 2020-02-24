# ts\_machine
ts\_machine はニコニコ生放送のタイムシフト予約を自動化するためのツールです。ニコニコ生放送内を検索し、ヒットした番組をタイムシフト予約します。

## セットアップ
### インストール
```sh
pip install ts_machine
```

### 設定
設定ファイルは以下の2つです。それぞれデフォルトの場所に配置して、適宜編集してください。

ファイル|デフォルトの場所|役割
:--|:--|:--
[config/config.toml](config/config.toml)|`~/.config/tsm/config.toml`|メインの設定ファイル
[config/filters.json](config/filters.json)|`~/.config/tsm/filters.json`|タイムシフト対象の生放送を絞り込む際に使われる高度なフィルタ

### テスト実行
`tsm -s` を実行すると、タイムシフト予約の対象となっている生放送を列挙します。タイムシフト予約したい生放送が列挙されているかどうか確認してください。

`tsm` を引数なしで実行すると、実際にタイムシフト予約を行い、結果を出力します。期待通りに動作するかどうか確認してください。

### ジョブ管理システムへの登録
`tsm` コマンドを cron 等のジョブ管理システムに登録してください。登録方法はそれぞれのジョブ管理システムのドキュメントを参照してください。

## 注意点
### niconico の利用規約
利用する前に以下の利用規約を読んでください。

  - [niconico コンテンツ検索APIガイド](https://site.nicovideo.jp/search-api-docs/search.html)のAPI利用規約
  - [ニコニコ生放送利用規約](https://site.live.nicovideo.jp/rule.html)
  - [niconico規約](https://account.nicovideo.jp/rules/account)
  - [サイトご利用にあたって](http://info.nicovideo.jp/base/term.html)

### ライセンス
[LICENSE](LICENSE) を確認してください。
