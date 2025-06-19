0. Web Programming
1. Hypertext Markup Language (HTML)
2. ## CSS
   1. The Document Object Model (DOM): interneal representation of an html page. Hierarchical tree.
   2. selector
      1. pseudo selector: different states of various elements
      2. contextual selector
      3. element
      4. attribute
   3. property
   4. value
   5. colors
      1. name
      2. rgb
      3. hex
      4. hsl
   6. units of measure
      1. px
      2. em
      3. %
      4. in
      5. cm
   7. Location of stules
      1. inline
      2. embedded style sheet: use <style></style> element within the <head> element
      3. external style sheet (preferred): <link rel="stylesheet" href="style.css">
   8. The cascade: specificity
      1. inline
      2. id + additional selector
      3. id selector
      4. class
      5. embedded
      6. external css file
3. PHP
4. JavaScript
5. Internet Protocols
6. TCP/IP
7. Domain Name System (DNS)
8. Root Name Server
9. Name Server
10. ARPANET
11. Name Levels
   1.  top-level domain (TLD)
   2.  second-level domain (SLD)
   3.  generic top-level domain (gTLD)
   4.  country code top-level domain (ccTLD)
   5.  internationalized top-level domain (IDN)
12. internet corporation for assigned names & numbers (ICANN)
13. registrar
14. reseller
15. registrant
16. client-server model
17. uniform resource locators (URL)
18. web servers
19. semantic markup
20. client
21. host
22. bootstrap
23. address resolution [104]
24. root name server
25. domain: realm of administrative autonomy, authority or control
26. port
27. path
28. query string
29. fragment
30. hypertext transfer protocol (HTTP)
31. HTTP headers
32. request headers
33. response headers
34. HTTP request methods
    1.  GET request: is not secure for forms? displays form input in URL.
    2.  POST request: does not display user input in URL, making it more secure? stores input in http header insteads.
    3.  HEAD request
    4.  CONNECT
    5.  TRACE
    6.  OPTIONS
35. response codes
36. web browsers
37. browser rendering (download, parse, layout, fetch assets)
38. browser caching
39. application stack
    1.  WAMP
    2.  LAMP
    3.  WISA
    4.  JAM
40. user datagram protocol (UDP)
41. Internet
42. world wide web (WWW)
43. Bandwidth
44. scale
45. / [61-62]
46. packet switched networks
47. circuit switched networks
48. sr. Tim Berners-Lee 1992
49. / [65][67]
50. web applications
51. static
52. desktop applications
53. dynamic
54. web 2.0
55. evolving complexity
56. client machines
57. server machines
58. server types
    1.  web servers
    2.  application servers
    3.  database servers
    4.  mail servers
    5.  media servers
    6.  authentication servers
59. server installations
    1.  server farm
    2.  load balancers
    3.  failober redundancy
    4.  server racks
    5.  data centers
    6.  cloud services
60. cache
61. browser rendering performance
    1.  TTFB
    2.  FP
    3.  FCP
    4.  FMP
    5.  LCP
    6.  TTI
    7.  on load
    8.  CLS-A
62. domain name registration process
    1.  registrant searches for available domain using registrar or reseller web portal [117]
    2.  registrar queries TLD registry operator  to check domain availability [121]
    3.  if available registrant pays for domain and provides WHOIS information [115]
    4.  registrar pushes WHOIS information of new domain to TLD registry operator
    5.  Registry operator adds WHOIS information to its authoritative list
    6.  registry operator will push DNS information for new domain to name servers  for the TLD [123]
63.  Address Resolution Process
     1. client requests domain
     2. client checks local DNS cache for the IP addresses of the requested domain
     3. if domain is not in local cache, computer requests IP address for domain name from primary DNS server
     4. if domain is not in primary DNS server, it sends out request to the Root Name Server
     5. Root Name Server returns address of relevant Top-Level Domain (TLD) server
     6. DNS server requests DNS information from provided TLD server.
     7. TLD server returns IP addresses of the authoritative DNS servers for requested domains.
     8. DNS server requests IP address for originally requested domain from one of the site's authoritative DNS servers. When received, it will save it in its own DNS cache.
     9. DNS server returns IP address of requested domain
     10. client computer can finally make its request of the domain
64.  WHOIS information
65.  TLD name servers
66.  Web Portal: singlle web page that aggregates content from multiple other systems or servers [98]
67.  Authoritative DNS servers: source of info about names in a zone
68.  TLD registry operator
     1.   has an authoritative list of all domains for a TLD
69.  Certificate Authority
     1.   SSL
     2.   TLS
70. Encryption
    1. Browser uses public key to used by client to encrypt and send messsage
    2. Server uses private key to decrypt message and retrieve session key
71. HTML Anatomy
    1.  <!DOCTYPE>
    2.  <html> </html>
    3.  <head> </head>
    4.  <body> </body>
        1.  p
        2.  h
        3.  div
    5.  <b>
    6.  <em>
    7.  <i>
    8.  <mark>
    9.  <small>
    10. <strong>
    11. <sub> // subscript
    12. <sup> // superscript
    13. Nesting
    14. Lists
        1. <ul> // unordered list
        2. <ol> // ordered list
        3. <li> // list item
        4. ==============================
        5. <dl> // description list
        6. <dt> // term
        7. <dd> // description oof term 
     15. <div> // division
     16. <header>
     17. <main>
     18. <nav>
     19. <footer>
     20. <a href="...">I'm not a Hyperlink</a>
     21. Absolute & Relative Hyperlinks
     22. <input>
     23. <label>
     24. <datatlist>
     25. <embed>
     26. <xmp>
     27. <section>
     28. <article>
72. Advantages of Semantic Markup
     1.  maintainability
     2.  faster
     3.  accessibility
     4.  search engine optimization
## Bootstrap
- framework
- MaxCDN
- provides classes with predefined css rules?
- spans
## AngularJS
- html attributes = Directives
- binds data to html with *Expressions*
- add script tag
- binding view to model
- ng-directives
- angularJS expressions support filters while javascript expressions do not. what are filters?
- two curly braces vs ng-bind
- $scope.name: ng-model=name
- var = global scope
- let = block scope

## Server-Side

### Responsabilities
- handle HTTP connections
- responding to requests
- manages permissions and access
- encrypts and compresses data
- manages domains and URLs

### LAMP stack
- linux os
- apache web server
  - PHP core: main features
  - extension layer
  - zend engine
- mySQL
- PHP

### Running PHP Locally
- start web server environment
- local web server requests local PHP resource
- web server delegates execution to bundled PHP module
- PHP execution output return to browser
- browser receives response and displays output

## Logical-Conditional Functions
