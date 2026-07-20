package com.calibreweb.reader.data

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.File

/**
 * Manages books stored on the device for offline reading: their files, covers,
 * unzipped EPUB working directories, and a JSON metadata index. Mirrors the
 * web PWA's "Make Available Offline" behaviour.
 */
class LibraryRepository(context: Context, private val opds: OpdsClient) {

    private val filesDir = context.filesDir
    private val booksDir = File(filesDir, "books").apply { mkdirs() }
    private val coversDir = File(filesDir, "covers").apply { mkdirs() }
    private val epubRoot = File(filesDir, "epub").apply { mkdirs() }
    private val indexFile = File(filesDir, "library.json")

    private val json = Json { ignoreUnknownKeys = true; prettyPrint = true }
    private val mutex = Mutex()

    private val _books = MutableStateFlow(loadIndex())
    val books: StateFlow<List<DownloadedBook>> = _books.asStateFlow()

    private fun loadIndex(): List<DownloadedBook> = try {
        if (indexFile.exists()) json.decodeFromString(indexFile.readText()) else emptyList()
    } catch (e: Exception) {
        emptyList()
    }

    private fun persist(list: List<DownloadedBook>) {
        runCatching { indexFile.writeText(json.encodeToString(list)) }
    }

    fun find(id: String, format: String): DownloadedBook? =
        _books.value.firstOrNull { it.id == id && it.format.equals(format, ignoreCase = true) }

    fun isDownloaded(id: String, format: String): Boolean = find(id, format) != null

    fun bookFile(book: DownloadedBook): File = File(booksDir, book.fileName)

    fun coverFile(book: DownloadedBook): File? =
        book.coverFileName?.let { File(coversDir, it) }?.takeIf { it.exists() }

    /** Working directory for an EPUB's unzipped contents. */
    fun epubDir(book: DownloadedBook): File = File(epubRoot, book.id + "_" + book.format)

    /**
     * Downloads a book (and its cover) for offline use. [onProgress] reports the
     * book file download 0..100.
     */
    suspend fun download(
        book: OpdsBook,
        format: OpdsFormat,
        onProgress: (Int) -> Unit,
    ): DownloadedBook {
        val ext = format.format.lowercase()
        val fileName = "${book.id}.$ext"
        val dest = File(booksDir, fileName)
        opds.download(format.downloadPath, dest, onProgress)

        var coverName: String? = null
        book.coverPath?.let { coverPath ->
            runCatching {
                val coverDest = File(coversDir, "${book.id}.jpg")
                opds.download(coverPath, coverDest) {}
                coverName = coverDest.name
            }
        }

        val entry = DownloadedBook(
            id = book.id,
            format = ext,
            title = book.title,
            authors = book.authorLine,
            fileName = fileName,
            coverFileName = coverName,
            sizeBytes = dest.length(),
            addedAt = System.currentTimeMillis(),
        )
        upsert(entry)
        return entry
    }

    suspend fun remove(book: DownloadedBook) = mutex.withLock {
        File(booksDir, book.fileName).delete()
        book.coverFileName?.let { File(coversDir, it).delete() }
        epubDir(book).deleteRecursively()
        val updated = _books.value.filterNot { it.id == book.id && it.format == book.format }
        _books.value = updated
        persist(updated)
    }

    suspend fun updateEpubProgress(book: DownloadedBook, spineIndex: Int, percent: Int) =
        replace(book.id, book.format) { it.copy(epubSpineIndex = spineIndex, progressPercent = percent) }

    suspend fun updatePdfProgress(book: DownloadedBook, page: Int, percent: Int) =
        replace(book.id, book.format) { it.copy(pdfPage = page, progressPercent = percent) }

    private suspend fun upsert(entry: DownloadedBook) = mutex.withLock {
        val updated = _books.value.filterNot { it.id == entry.id && it.format == entry.format } + entry
        _books.value = updated.sortedByDescending { it.addedAt }
        persist(_books.value)
    }

    private suspend fun replace(
        id: String,
        format: String,
        transform: (DownloadedBook) -> DownloadedBook,
    ) = mutex.withLock {
        var changed = false
        val updated = _books.value.map {
            if (it.id == id && it.format == format) { changed = true; transform(it) } else it
        }
        if (changed) {
            _books.value = updated
            persist(updated)
        }
    }

    fun totalBytes(): Long = _books.value.sumOf { it.sizeBytes }
}
