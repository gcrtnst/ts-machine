# ts\_machine
ts\_machine はニコニコ生放送のタイムシフト予約を自動化するためのツールです。
ニコニコ生放送内を検索し、ヒットした番組をタイムシフト予約します。
一般会員での利用を想定しています。

## セットアップ
### インストール
```
pip install git+https://github.com/gcrtnst/ts_machine.git
```

### 設定ファイルの用意
設定ファイルは必須です。

このレポジトリの config ディレクトリに設定ファイルのサンプルがあります。
設定項目の詳細はこのディレクトリの中にある config.toml に書かれています。

config.toml のデフォルトの場所は \~/.config/tsm/config.toml です。
ただし、これは `tsm` コマンドの `-c` 引数で変更することができます。

### テスト実行
`tsm` コマンドを `-s` 引数付きで実行すると、タイムシフト予約の対象となっている生放送を列挙します。
タイムシフト予約したい生放送が列挙されているかどうか確認してください。

`tsm` コマンドを引数なしで実行すると、実際にタイムシフト予約を行い、結果を出力します。
期待通りに動作するか確認してください。

### ジョブ管理システムの設定
`tsm` コマンドを cron 等のジョブ管理システムに登録してください。
登録方法はそれぞれのジョブ管理システムのドキュメントを参照してください。

## 注意点
### niconico の利用規約
利用する前に以下の利用規約を読んでください。

  - [niconico コンテンツ検索APIガイド](https://site.nicovideo.jp/search-api-docs/search.html)のAPI利用規約
  - [ニコニコ生放送利用規約](https://site.live.nicovideo.jp/rule.html)
  - [niconico規約](https://account.nicovideo.jp/rules/account)
  - [その他の利用規約](http://info.nicovideo.jp/base/term.html)

### ライセンス
[LICENSE](LICENSE) を確認してください。

### その他
  - 設定ファイル及び cookieJar のパーミッションは適切に設定してください。
  - ニコニコ生放送のサーバーに過度な負荷を掛けないようにしてください。
