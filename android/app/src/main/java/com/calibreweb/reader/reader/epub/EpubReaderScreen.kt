package com.calibreweb.reader.reader.epub

import android.webkit.WebView
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.calibreweb.reader.ui.rememberApp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EpubReaderScreen(bookId: String, format: String, onBack: () -> Unit) {
    val app = rememberApp()
    val context = LocalContext.current
    val book = remember(bookId, format) { app.library.find(bookId, format) }

    if (book == null) {
        MissingBook(onBack)
        return
    }

    var epub by remember { mutableStateOf<EpubBook?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var index by remember { mutableIntStateOf(book.epubSpineIndex) }

    LaunchedEffect(book) {
        try {
            val opened = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                EpubBook.open(app.library.bookFile(book), app.library.epubDir(book))
            }
            epub = opened
            index = book.epubSpineIndex.coerceIn(0, opened.spineFiles.lastIndex)
        } catch (e: Exception) {
            error = e.message ?: "Failed to open book"
        }
    }

    // Persist reading position whenever the chapter changes.
    LaunchedEffect(index, epub) {
        val e = epub ?: return@LaunchedEffect
        val percent = ((index + 1) * 100) / e.spineFiles.size
        app.library.updateEpubProgress(book, index, percent)
    }

    val webView = remember {
        WebView(context).apply {
            @Suppress("SetJavaScriptEnabled")
            settings.javaScriptEnabled = true
            settings.allowFileAccess = true
            @Suppress("DEPRECATION")
            settings.allowFileAccessFromFileURLs = true
            @Suppress("DEPRECATION")
            settings.allowUniversalAccessFromFileURLs = true
            settings.builtInZoomControls = true
            settings.displayZoomControls = false
            settings.setSupportZoom(true)
        }
    }
    DisposableEffect(Unit) {
        onDispose { webView.destroy() }
    }

    val total = epub?.spineFiles?.size ?: 0

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        book.title,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
        bottomBar = {
            if (epub != null) {
                Column {
                    LinearProgressIndicator(
                        progress = if (total > 0) (index + 1).toFloat() / total else 0f,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Button(enabled = index > 0, onClick = { if (index > 0) index-- }) {
                            Icon(Icons.Filled.ChevronLeft, contentDescription = null)
                            Text("Prev")
                        }
                        Text("${index + 1} / $total")
                        Button(
                            enabled = index < total - 1,
                            onClick = { if (index < total - 1) index++ },
                        ) {
                            Text("Next")
                            Icon(Icons.Filled.ChevronRight, contentDescription = null)
                        }
                    }
                }
            }
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentAlignment = Alignment.Center,
        ) {
            when {
                error != null -> Text(
                    error!!,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(24.dp),
                )
                epub == null -> CircularProgressIndicator()
                else -> AndroidView(
                    factory = { webView },
                    modifier = Modifier.fillMaxSize(),
                ) { wv ->
                    val e = epub
                    if (e != null && index in e.spineFiles.indices) {
                        val url = "file://" + e.spineFiles[index].absolutePath
                        if (wv.tag != url) {
                            wv.tag = url
                            wv.scrollTo(0, 0)
                            wv.loadUrl(url)
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MissingBook(onBack: () -> Unit) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Reader") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
            Text("This book is no longer available offline.")
        }
    }
}
