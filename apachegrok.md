Graylog apache access log grok
```sh
%{IP} - - \[%{HTTPDATE}\] "%{WORD:REQUEST} %{DATA:HTTPMESSAGE}" %{INT:HTTPCODE} %{INT:UNWANTED} "-" %{GREEDYDATA:USERAGENT}
```
