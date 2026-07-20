package com.calibreweb.reader.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.calibreweb.reader.CalibreApp
import com.calibreweb.reader.data.DownloadedBook
import com.calibreweb.reader.data.OpdsBook
import com.calibreweb.reader.data.OpdsFormat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class BrowseUiState(
    val loading: Boolean = false,
    val books: List<OpdsBook> = emptyList(),
    val error: String? = null,
    val query: String = "",
    val message: String? = null,
)

class LibraryViewModel(app: CalibreApp) : ViewModel() {

    private val opds = app.opdsClient
    private val repo = app.library

    private val _ui = MutableStateFlow(BrowseUiState())
    val ui: StateFlow<BrowseUiState> = _ui.asStateFlow()

    /** Books currently stored offline. */
    val downloaded: StateFlow<List<DownloadedBook>> = repo.books

    /** Active download progress keyed by "id.format", value 0..100. */
    private val _progress = MutableStateFlow<Map<String, Int>>(emptyMap())
    val progress: StateFlow<Map<String, Int>> = _progress.asStateFlow()

    init {
        loadRecent()
    }

    fun onQueryChange(q: String) {
        _ui.update { it.copy(query = q) }
    }

    fun loadRecent() = load { opds.fetchRecent().books }

    fun submitSearch() {
        val q = _ui.value.query.trim()
        if (q.isEmpty()) loadRecent() else load { opds.search(q).books }
    }

    private fun load(block: suspend () -> List<OpdsBook>) {
        viewModelScope.launch {
            _ui.update { it.copy(loading = true, error = null) }
            try {
                val books = block()
                _ui.update { it.copy(loading = false, books = books, error = null) }
            } catch (e: Exception) {
                _ui.update {
                    it.copy(loading = false, error = e.message ?: "Could not load library")
                }
            }
        }
    }

    fun download(book: OpdsBook, format: OpdsFormat) {
        val key = keyOf(book.id, format.format)
        if (_progress.value.containsKey(key)) return
        viewModelScope.launch {
            _progress.update { it + (key to 0) }
            try {
                repo.download(book, format) { p ->
                    _progress.update { it + (key to p) }
                }
            } catch (e: Exception) {
                _ui.update { it.copy(message = "Download failed: ${e.message}") }
            } finally {
                _progress.update { it - key }
            }
        }
    }

    fun remove(bookId: String, format: String) {
        viewModelScope.launch {
            repo.find(bookId, format)?.let { repo.remove(it) }
        }
    }

    fun consumeMessage() {
        _ui.update { it.copy(message = null) }
    }

    companion object {
        fun keyOf(id: String, format: String) = "$id.${format.lowercase()}"
    }
}
