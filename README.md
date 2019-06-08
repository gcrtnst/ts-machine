# ts-machine
ts-machine はニコニコ生放送のタイムシフト予約を自動化するためのツールです。
ニコニコ生放送内を検索し、ヒットした番組をタイムシフト予約します。
一般会員での利用を想定しています。

## 使い方

  - 設定ファイルが必須です。
  - 実行すると設定された通りに検索を行い、ヒットした番組をタイムシフト予約します。
  - cron 等で定期的に実行することを意図して制作しています。

### 設定ファイルの用意

このレポジトリの config ディレクトリの中身を \~/.config/tsm ディレクトリにコピーしてください。

そして、\~/.config/tsm/config.toml 及び \~/.config/tsm/filters.json を編集してください。
設定項目についての説明は config.toml にあります。とりあえずメールとパスワードを設定すれば動作はします。
必要に応じて `tsm.py -s` を実行し、タイムシフト予約の対象になっている生放送を確認してください。

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
