# ts-machine
ts-machine はニコニコ生放送のタイムシフト予約を自動化するためのツールです。
ニコニコ生放送内を検索し、ヒットした番組をタイムシフト予約します。
一般会員での利用を想定しています。

## 使い方

  - 設定ファイルが必須です。
  - 実行すると設定された通りに検索を行い、ヒットした番組をタイムシフト予約します。
  - cron 等で定期的に実行することを意図して制作しています。

```
usage: tsm.py [-h] [-s] config

positional arguments:
  config          TOML-formatted configuration file

optional arguments:
  -h, --help      show this help message and exit
  -s, --simulate  simulate timeshift reservation
```

### 設定ファイル(TOML)
|テーブル|キー|型|省略可能か|デフォルト値|説明|
|:-|:-|:-|:-|:-|:-|
|login|mail|string|no||メールアドレス|
||password|string|no||パスワード|
||cookieJar|string|yes||クッキー保存先のファイル。LWPCookieJar を使用します。|
|search|q|string|no||検索キーワード|
||targets|string array|yes|`["title", "description", "tags"]`|検索対象。[コンテンツ検索API](https://site.nicovideo.jp/search-api-docs/search.html)のフィールドを指定できます。キーワード検索の場合は`["title", "description", "tags"]`、タグ検索の場合は`["tagsExact"]`を指定してください。|
||sort|string|yes|`"+startTime"`|タイムシフト予約の登録順序。[コンテンツ検索API](https://site.nicovideo.jp/search-api-docs/search.html)の \_sort クエリパラメータと同様に指定してください。|
||userId|integer array|yes||放送者のID|
||channelId|integer array|yes||チャンネルID|
||communityId|integer array|yes||コミュニティID|
||providerType|string array|yes||放送元種別(`"official"`, `"community"`, `"channel"`)|
||tags|string array|yes||タグ|
||openBefore|string|yes||今から何時間以内に開場するか("1h30m" などの形式で指定)|
||openAfter|string|yes||今から何時間以降に開場するか("1h30m" などの形式で指定)|
||startBefore|string|yes||今から何時間以内に放送開始するか("1h30m" などの形式で指定)|
||startAfter|string|yes|`"30m"`|今から何時間以降に放送開始するか("1h30m" などの形式で指定)|
||scoreTimeshiftReserved|integer|yes||タイムシフト予約者数の下限|
||memberOnly|bool|yes||チャンネル・コミュニティ限定か|
||ppv|bool|yes||有料放送か(ネットチケットが必要か)|
|misc|timeout|integer or float|yes|`300`|サーバーのレスポンスが受信できなくなってから指定秒数経過すると処理を中断します。|
||timeshiftLimit|integer|yes|`10`|タイムシフト予約総数の上限|

#### 設定例
今から2時間以内に放送開始される、公式の将棋番組をタイムシフト予約する場合の設定。
```toml
[login]
mail = "email@example.com"
password = "password"
cookieJar = "/path/to/cookiejar"

[search]
q = "将棋"
providerType = "official"
startBefore = "2h"
```

### エラー時の動作
以下のエラーが発生した場合、何もエラーを出力せずに次の番組の予約に移ります。
  - 予約しようとした番組が既に予約済みだった
  - タイムシフト予約が申し込み期限切れだった

その他のエラーが発生した場合、エラーを出力して強制終了します。

## 注意点
  - 設定ファイル及び cookieJar のパーミッションは適切に設定してください。
  - ニコニコ生放送のサーバーに過度な負荷を掛けないようにしてください。
  - 定期実行する場合は、cookieJar を設定することをおすすめします。設定しない場合、他のブラウザソフト等でセッション切れが頻繁に起こります。
