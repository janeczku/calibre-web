package com.calibreweb.reader.data

import kotlinx.serialization.Serializable

/** An acquisition (downloadable) format advertised for a book in the OPDS feed. */
data class OpdsFormat(
    val format: String,      // e.g. "EPUB", "PDF"
    val mimeType: String,    // e.g. "application/epub+zip"
    val downloadPath: String, // relative path, e.g. /opds/download/12/epub/
    val sizeBytes: Long,
) {
    /** Formats the in-app readers can open. */
    val isReadable: Boolean
        get() = format.lowercase() in READABLE_FORMATS

    companion object {
        val READABLE_FORMATS = setOf("epub", "kepub", "pdf")
    }
}

/** A book as returned by an OPDS acquisition feed (e.g. /opds/new). */
data class OpdsBook(
    val id: String,          // book id parsed from the download/cover link, or uuid fallback
    val title: String,
    val authors: List<String>,
    val summary: String,
    val coverPath: String?,  // relative path to cover image, needs auth
    val formats: List<OpdsFormat>,
) {
    val authorLine: String get() = authors.joinToString(", ")
}

/** A parsed OPDS acquisition feed page. */
data class OpdsFeed(
    val books: List<OpdsBook>,
    val nextPath: String?,   // relative path for the next page, or null
)

/**
 * Metadata for a book stored on the device for offline reading. Persisted as
 * JSON by [LibraryRepository].
 */
@Serializable
data class DownloadedBook(
    val id: String,
    val format: String,          // lowercase, e.g. "epub", "pdf"
    val title: String,
    val authors: String,
    val fileName: String,        // relative to the books directory
    val coverFileName: String?,  // relative to the covers directory, or null
    val sizeBytes: Long,
    val addedAt: Long,
    // Reading progress
    val progressPercent: Int = 0,
    // EPUB: index into the spine of the last-read chapter
    val epubSpineIndex: Int = 0,
    // PDF: last-read page (0-based)
    val pdfPage: Int = 0,
) {
    val isPdf: Boolean get() = format.equals("pdf", ignoreCase = true)
    val isEpub: Boolean get() = format.equals("epub", ignoreCase = true) ||
        format.equals("kepub", ignoreCase = true)
}
