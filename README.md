# ts-machine
ts-machine はニコニコ生放送のタイムシフト予約を自動化するためのツールです。
ニコニコ生放送内を検索し、ヒットした番組をタイムシフト予約します。
一般会員での利用を想定しています。

## 使い方

  - 設定ファイルが必須です。
  - 実行すると設定された通りに検索を行い、ヒットした番組をタイムシフト予約します。
  - cron 等で定期的に実行することを意図して制作しています。

```
usage: tsm.py [-h] [-c CONFIG] [-s [N]]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        TOML-formatted configuration file (default:
                        ~/.tsm)
  -s [N], --search [N]  search only mode; N specifies maximum number of
                        programs to search (default: 10)
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
||categoryTags|string array|yes||カテゴリタグ|
||viewCounterMin|integer|yes||来場者数の下限|
||viewCounterMax|integer|yes||来場者数の上限|
||commentCounterMin|integer|yes||コメント数の下限|
||commentCounterMax|integer|yes||コメント数の上限|
||openBefore|string|yes||今から何時間以内に開場するか(`"1h30m"` などの形式で指定)|
||openAfter|string|yes||今から何時間以降に開場するか(`"1h30m"` などの形式で指定)|
||startBefore|string|yes||今から何時間以内に放送開始するか(`"1h30m"` などの形式で指定)|
||startAfter|string|yes|`"30m"`|今から何時間以降に放送開始するか(`"1h30m"` などの形式で指定)|
||liveEndBefore|string|yes||今から何時間以内に放送終了するか(`"1h30m"` などの形式で指定)|
||liveEndAfter|string|yes||今から何時間以降に放送終了するか(`"1h30m"` などの形式で指定)|
||scoreTimeshiftReservedMin|integer|yes||タイムシフト予約者数の下限|
||scoreTimeshiftReservedMax|integer|yes||タイムシフト予約者数の上限|
||memberOnly|bool|yes||チャンネル・コミュニティ限定か|
||liveStatus|string array|yes|`["reserved"]`|放送ステータス(`"past"`、`"onair"`、`"reserved"`)|
||ppv|bool|yes||有料放送か(ネットチケットが必要か)|
|warn|registrationExpired|bool|yes|`true`|タイムシフト予約が申し込み期限切れだった場合に警告します。|
||maxReservation|bool|yes|`true`|タイムシフトの予約上限に達した場合に警告します。|
|misc|overwrite|bool|yes|`false`|視聴期限が切れたタイムシフト予約を上書きします。|
||timeout|number|yes|`300`|サーバーのレスポンスが受信できなくなってから指定秒数経過すると処理を中断します。|
||userAgent|string|yes|`ts-machine (private app)`|HTTP リクエストの User-Agent ヘッダ|
||context|string|yes|`ts-machine (private app)`|[コンテンツ検索API](https://site.nicovideo.jp/search-api-docs/search.html)の \_context クエリパラメータ|

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
  - 定期実行する場合は、cookieJar を設定することをおすすめします。設定しない場合、他のブラウザソフト等でセッション切れが頻繁に起こります。
