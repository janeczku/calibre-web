<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:dc="http://purl.org/dc/terms/"
      xmlns:opds="http://opds-spec.org/2010/catalog">
  <id>urn:uuid:433a5d6a-0b8c-4933-af65-4ca4f02763eb</id>

  <link rel="related"
        href="/opds-catalogs/vampire.farming.xml"
        type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <link rel="self"
        href="/opds-catalogs/unpopular.xml"
        type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <link rel="start"
        href="/opds-catalogs/root.xml"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  <link rel="up"
        href="/opds-catalogs/root.xml"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>

  <title>Unpopular Publications</title>
  <updated>2010-01-10T10:01:11Z</updated>
  <author>
    <name>Spec Writer</name>
    <uri>http://opds-spec.org</uri>
  </author>

  <entry>
    <title>Bob, Son of Bob</title>
    <id>urn:uuid:6409a00b-7bf2-405e-826c-3fdff0fd0734</id>
    <updated>2010-01-10T10:01:11Z</updated>
    <author>
      <name>Bob the Recursive</name>
      <uri>http://opds-spec.org/authors/1285</uri>
    </author>
    <dc:language>en</dc:language>
    <dc:issued>1917</dc:issued>
    <category scheme="http://www.bisg.org/standards/bisac_subject/index.html"
              term="FIC020000"
              label="FICTION / Men's Adventure"/>
    <summary>The story of the son of the Bob and the gallant part he played in
      the lives of a man and a woman.</summary>
    <link rel="http://opds-spec.org/image"
          href="/covers/4561.lrg.png"
          type="image/png"/>
    <link rel="http://opds-spec.org/image/thumbnail"
          href="/covers/4561.thmb.gif"
          type="image/gif"/>

    <link rel="alternate"
          href="/opds-catalogs/entries/4571.complete.xml"
          type="application/atom+xml;type=entry;profile=opds-catalog"
          title="Complete Catalog Entry for Bob, Son of Bob"/>

    <link rel="http://opds-spec.org/acquisition"
          href="/content/free/4561.epub"
          type="application/epub+zip"/>
    <link rel="http://opds-spec.org/acquisition"
          href="/content/free/4561.mobi"
          type="application/x-mobipocket-ebook"/>
  </entry>

  <entry>
    <title>Modern Online Philately</title>
    <id>urn:uuid:7b595b0c-e15c-4755-bf9a-b7019f5c1dab</id>
    <author>
      <name>Stampy McGee</name>
      <uri>http://opds-spec.org/authors/21285</uri>
    </author>
    <author>
      <name>Alice McGee</name>
      <uri>http://opds-spec.org/authors/21284</uri>
    </author>
    <author>
      <name>Harold McGee</name>
      <uri>http://opds-spec.org/authors/21283</uri>
    </author>
    <updated>2010-01-10T10:01:10Z</updated>
    <rights>Copyright (c) 2009, Stampy McGee</rights>
    <dc:identifier>urn:isbn:978029536341X</dc:identifier>
    <dc:publisher>StampMeOnline, Inc.</dc:publisher>
    <dc:language>en</dc:language>
    <dc:issued>2009-10-01</dc:issued>
    <content type="text">The definitive reference for the web-curious
      philatelist.</content>
    <link rel="http://opds-spec.org/image"
          href="/covers/11241.lrg.jpg"
          type="image/jpeg"/>

    <link rel="http://opds-spec.org/acquisition/buy"
          href="/content/buy/11241.epub"
          type="application/epub+zip">
      <opds:price currencycode="USD">18.99</opds:price>
      <opds:price currencycode="GBP">11.99</opds:price>
    </link>
  </entry>
</feed>
