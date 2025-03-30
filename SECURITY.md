# Security Policy

## Reporting a Vulnerability

Please report security issues to ozzie.fernandez.isaacs@googlemail.com

## Supported Versions

To receive fixes for security vulnerabilities it is required to always upgrade to the latest version of Calibre-Web. See https://github.com/janeczku/calibre-web/releases/latest for the latest release.

## History

| Fixed in      | Description                                                                                                                      | CVE number     |
|---------------|----------------------------------------------------------------------------------------------------------------------------------|----------------|
| 3rd July 2018 | Guest access acts as a backdoor                                                                                                  |                |
| V 0.6.7       | Hardcoded secret key for sessions                                                                                                | CVE-2020-12627 |
| V 0.6.13      | Calibre-Web Metadata cross site scripting                                                                                        | CVE-2021-25964 |
| V 0.6.13      | Name of Shelves are only visible to users who can access the corresponding shelf Thanks to @ibarrionuevo                         |                |
| V 0.6.13      | JavaScript could get executed in the description field. Thanks to @ranjit-git  and Hagai Wechsler (WhiteSource)                  |                |
| V 0.6.13      | JavaScript could get executed in a custom column of type "comment" field                                                         |                |
| V 0.6.13      | JavaScript could get executed after converting a book to another format with a title containing javascript code                  |                |
| V 0.6.13      | JavaScript could get executed after converting a book to another format with a username containing javascript code               |                |
| V 0.6.13      | JavaScript could get executed in the description series, categories or publishers title                                          |                |
| V 0.6.13      | JavaScript could get executed  in the shelf title                                                                                |                |
| V 0.6.13      | Login with the old session cookie after logout. Thanks to @ibarrionuevo                                                          |                |
| V 0.6.14      | CSRF was possible. Thanks to @mik317 and Hagai Wechsler (WhiteSource)                                                            | CVE-2021-25965 |
| V 0.6.14      | Migrated some routes to POST-requests (CSRF protection). Thanks to @scara31                                                      | CVE-2021-4164  |
| V 0.6.15      | Fix for "javascript:" script links in identifier. Thanks to @scara31                                                             | CVE-2021-4170  |
| V 0.6.15      | Cross-Site Scripting vulnerability on uploaded cover file names. Thanks to @ibarrionuevo                                         |                |
| V 0.6.15      | Creating public shelfs is now denied if user is missing the edit public shelf right. Thanks to @ibarrionuevo                     |                |
| V 0.6.15      | Changed error message in case of trying to delete a shelf unauthorized. Thanks to @ibarrionuevo                                  |                |
| V 0.6.16      | JavaScript could get executed on authors page. Thanks to @alicaz                                                                 | CVE-2022-0352  |
| V 0.6.16      | Localhost can no longer be used to upload covers. Thanks to @scara31                                                             | CVE-2022-0339  |
| V 0.6.16      | Another case where public shelfs could be created without permission is prevented. Thanks to @nhiephon                           | CVE-2022-0273  |
| V 0.6.16      | It's prevented to get the name of a private shelfs. Thanks to @nhiephon                                                          | CVE-2022-0405  |
| V 0.6.17      | The SSRF Protection can no longer be bypassed via an HTTP redirect. Thanks to @416e6e61                                          | CVE-2022-0767  |
| V 0.6.17      | The SSRF Protection can no longer be bypassed via 0.0.0.0 and it's ipv6 equivalent. Thanks to @r0hanSH                           | CVE-2022-0766  |
| V 0.6.18      | Possible SQL Injection is prevented in user table  Thanks to Iman Sharafaldin (Forward Security)                                 | CVE-2022-30765 |
| V 0.6.18      | The SSRF protection no longer can be bypassed by IPV6/IPV4 embedding. Thanks to  @416e6e61                                       | CVE-2022-0939  |
| V 0.6.18      | The SSRF protection no longer can be bypassed to connect to other servers in the local network. Thanks to @michaellrowley        | CVE-2022-0990  |
| V 0.6.20      | Credentials for emails are now stored encrypted                                                                                  |                |
| V 0.6.20      | Login is rate limited                                                                                                            |                |
| V 0.6.20      | Passwordstrength can be forced                                                                                                   |                |
| V 0.6.21      | SMTP server credentials are no longer returned to client                                                                         |                |
| V 0.6.21      | Cross-site scripting (XSS) stored in href bypasses filter using data wrapper no longer possible                                  |                |
| V 0.6.21      | Cross-site scripting (XSS) is no longer possible via pathchooser                                                                 |                |
| V 0.6.21      | Error Handling at non existent rating, language, and user downloaded books was fixed                                             |                |
| V 0.6.22      | Upload mimetype is checked to prevent malicious file content in the books library                                                |                |
| V 0.6.22      | Cross-site scripting (XSS) stored in comments section is prevented better (switching from lxml to bleach for sanitizing strings) |                |
| V 0.6.23      | Cookies are no longer stored for opds basic authentication and proxy authentication                                              |                |




## Statement regarding Log4j (CVE-2021-44228 and related)

Calibre-web is not affected by bugs related to Log4j. Calibre-Web is a python program, therefore not using Java, and not using the Java logging feature log4j. 
