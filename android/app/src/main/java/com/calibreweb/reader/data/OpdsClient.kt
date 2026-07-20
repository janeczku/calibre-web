package com.calibreweb.reader.data

import android.util.Xml
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Request
import org.xmlpull.v1.XmlPullParser
import java.io.File
import java.io.IOException
import java.io.InputStream
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

/**
 * Talks to a Calibre-Web server over its OPDS (Atom XML) catalog, using HTTP
 * Basic authentication. Handles browsing, searching, cover URLs and streaming
 * downloads.
 */
class OpdsClient(private val settings: SettingsStore) {

    private val authInterceptor = Interceptor { chain ->
        val builder = chain.request().newBuilder().header("User-Agent", USER_AGENT)
        if (chain.request().header("Authorization") == null) {
            settings.basicAuthHeader()?.let { builder.header("Authorization", it) }
        }
        chain.proceed(builder.build())
    }

    /** Shared client; also reused by Coil for authenticated cover loading. */
    val httpClient: OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    fun absoluteUrl(pathOrUrl: String): String {
        if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) return pathOrUrl
        val path = if (pathOrUrl.startsWith("/")) pathOrUrl else "/$pathOrUrl"
        return settings.baseUrl() + path
    }

    private fun requestFor(pathOrUrl: String): Request =
        Request.Builder().url(absoluteUrl(pathOrUrl)).build()

    /** Verifies the server URL and credentials by hitting the OPDS root. */
    suspend fun testConnection(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            httpClient.newCall(requestFor("/opds")).execute().use { resp ->
                when {
                    resp.isSuccessful -> Result.success(Unit)
                    resp.code == 401 -> Result.failure(IOException("Invalid username or password"))
                    else -> Result.failure(IOException("Server returned HTTP ${resp.code}"))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /** Fetches and parses one page of an OPDS acquisition feed. */
    suspend fun fetchFeed(pathOrUrl: String): OpdsFeed = withContext(Dispatchers.IO) {
        httpClient.newCall(requestFor(pathOrUrl)).execute().use { resp ->
            if (!resp.isSuccessful) throw IOException("HTTP ${resp.code} loading catalog")
            val body = resp.body ?: throw IOException("Empty response")
            body.byteStream().use { parseFeed(it) }
        }
    }

    /** Recently added books, paginated. */
    suspend fun fetchRecent(): OpdsFeed = fetchFeed("/opds/new")

    /** Full text search across the library. */
    suspend fun search(query: String): OpdsFeed {
        val encoded = URLEncoder.encode(query.trim(), "UTF-8")
        return fetchFeed("/opds/search?query=$encoded")
    }

    /** Streams a book download to [dest], reporting progress 0..100. */
    suspend fun download(pathOrUrl: String, dest: File, onProgress: (Int) -> Unit) =
        withContext(Dispatchers.IO) {
            httpClient.newCall(requestFor(pathOrUrl)).execute().use { resp ->
                if (!resp.isSuccessful) throw IOException("HTTP ${resp.code} downloading book")
                val body = resp.body ?: throw IOException("Empty download")
                val total = body.contentLength()
                dest.outputStream().use { out ->
                    body.byteStream().use { input ->
                        val buf = ByteArray(16 * 1024)
                        var readTotal = 0L
                        var n: Int
                        while (input.read(buf).also { n = it } != -1) {
                            out.write(buf, 0, n)
                            readTotal += n
                            if (total > 0) onProgress(((readTotal * 100) / total).toInt())
                        }
                    }
                }
            }
        }

    // ----------------------------- XML parsing -----------------------------

    private fun parseFeed(input: InputStream): OpdsFeed {
        val parser = Xml.newPullParser()
        parser.setFeature(XmlPullParser.FEATURE_PROCESS_NAMESPACES, false)
        parser.setInput(input, null)
        parser.nextTag()
        return readFeed(parser)
    }

    private fun readFeed(parser: XmlPullParser): OpdsFeed {
        val books = ArrayList<OpdsBook>()
        var nextPath: String? = null
        parser.require(XmlPullParser.START_TAG, null, "feed")
        while (parser.next() != XmlPullParser.END_TAG) {
            if (parser.eventType != XmlPullParser.START_TAG) continue
            when (parser.name) {
                "entry" -> readEntry(parser)?.let { books.add(it) }
                "link" -> {
                    val rel = parser.getAttributeValue(null, "rel")
                    val href = parser.getAttributeValue(null, "href")
                    if (rel == "next" && href != null) nextPath = relativePath(href)
                    skip(parser)
                }
                else -> skip(parser)
            }
        }
        return OpdsFeed(books, nextPath)
    }

    private fun readEntry(parser: XmlPullParser): OpdsBook? {
        parser.require(XmlPullParser.START_TAG, null, "entry")
        var title = ""
        var idText: String? = null
        var summary = ""
        var coverPath: String? = null
        val authors = ArrayList<String>()
        val formats = ArrayList<OpdsFormat>()

        while (parser.next() != XmlPullParser.END_TAG) {
            if (parser.eventType != XmlPullParser.START_TAG) continue
            when (parser.name) {
                "title" -> title = readNestedText(parser).trim()
                "id" -> idText = readNestedText(parser).trim()
                "author" -> readNestedText(parser).trim().let { if (it.isNotEmpty()) authors.add(it) }
                "content", "summary" -> summary = readNestedText(parser).trim()
                "link" -> {
                    val rel = parser.getAttributeValue(null, "rel").orEmpty()
                    val href = parser.getAttributeValue(null, "href")
                    val type = parser.getAttributeValue(null, "type").orEmpty()
                    val length = parser.getAttributeValue(null, "length")?.toLongOrNull() ?: 0L
                    val fmtTitle = parser.getAttributeValue(null, "title")
                    if (href != null) {
                        when {
                            rel.startsWith("http://opds-spec.org/acquisition") -> {
                                val fmt = (fmtTitle ?: formatFromType(type) ?: extFromPath(href)).uppercase()
                                formats.add(OpdsFormat(fmt, type, relativePath(href), length))
                            }
                            rel == "http://opds-spec.org/image" ->
                                coverPath = relativePath(href)
                            rel == "http://opds-spec.org/image/thumbnail" ->
                                if (coverPath == null) coverPath = relativePath(href)
                        }
                    }
                    skip(parser)
                }
                else -> skip(parser)
            }
        }

        if (title.isBlank()) return null
        val bookId = formats.firstOrNull()?.let { bookIdFromDownloadPath(it.downloadPath) }
            ?: coverPath?.let { bookIdFromCoverPath(it) }
            ?: idText?.substringAfterLast(':')
            ?: return null
        return OpdsBook(bookId, title, authors, summary, coverPath, formats)
    }

    /** Reads all text within the current element, ignoring nested tags. */
    private fun readNestedText(parser: XmlPullParser): String {
        val sb = StringBuilder()
        var depth = 1
        while (depth != 0) {
            when (parser.next()) {
                XmlPullParser.START_TAG -> depth++
                XmlPullParser.END_TAG -> depth--
                XmlPullParser.TEXT -> sb.append(parser.text)
                XmlPullParser.END_DOCUMENT -> return sb.toString()
            }
        }
        return sb.toString()
    }

    private fun skip(parser: XmlPullParser) {
        if (parser.eventType != XmlPullParser.START_TAG) throw IllegalStateException()
        var depth = 1
        while (depth != 0) {
            when (parser.next()) {
                XmlPullParser.END_TAG -> depth--
                XmlPullParser.START_TAG -> depth++
                XmlPullParser.END_DOCUMENT -> return
            }
        }
    }

    companion object {
        private const val USER_AGENT = "CalibreWebReader/1.0 (Android)"

        fun relativePath(href: String): String {
            if (!href.startsWith("http://") && !href.startsWith("https://")) return href
            val schemeEnd = href.indexOf("://") + 3
            val slash = href.indexOf('/', schemeEnd)
            return if (slash >= 0) href.substring(slash) else "/"
        }

        fun bookIdFromDownloadPath(path: String): String? {
            val parts = path.trim('/').split('/')
            val i = parts.indexOf("download")
            return if (i >= 0 && i + 1 < parts.size) parts[i + 1] else null
        }

        fun bookIdFromCoverPath(path: String): String? =
            path.trim('/').split('/').lastOrNull { it.toIntOrNull() != null }

        private fun extFromPath(path: String): String =
            path.trim('/').substringAfterLast('/', "").ifEmpty {
                path.trim('/').split('/').getOrElse(3) { "bin" }
            }

        private fun formatFromType(mime: String): String? = when {
            mime.contains("epub") -> "EPUB"
            mime.contains("pdf") -> "PDF"
            mime.contains("mobi") -> "MOBI"
            mime.contains("plain") -> "TXT"
            else -> null
        }
    }
}
