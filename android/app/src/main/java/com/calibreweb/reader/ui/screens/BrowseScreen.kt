package com.calibreweb.reader.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.calibreweb.reader.data.OpdsBook
import com.calibreweb.reader.data.OpdsFormat
import com.calibreweb.reader.ui.appViewModel
import com.calibreweb.reader.ui.components.BookCover
import com.calibreweb.reader.ui.formatBytes
import com.calibreweb.reader.ui.rememberApp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BrowseScreen(
    onOpenReader: (id: String, format: String, isPdf: Boolean) -> Unit,
    onNeedsSetup: () -> Unit,
) {
    val app = rememberApp()
    if (!app.settings.isConfigured) {
        LaunchedEffect(Unit) { onNeedsSetup() }
        return
    }

    val vm = appViewModel { LibraryViewModel(it) }
    val ui by vm.ui.collectAsStateWithLifecycle()
    val downloaded by vm.downloaded.collectAsStateWithLifecycle()
    val progress by vm.progress.collectAsStateWithLifecycle()

    var selected by remember { mutableStateOf<OpdsBook?>(null) }
    val sheetState = rememberModalBottomSheetState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Library") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 12.dp),
        ) {
            OutlinedTextField(
                value = ui.query,
                onValueChange = vm::onQueryChange,
                label = { Text("Search title, author…") },
                singleLine = true,
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { vm.submitSearch() }),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
            )

            when {
                ui.loading -> CenterBox {
                    CircularProgressIndicator()
                }
                ui.error != null -> CenterBox {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(ui.error!!, color = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.height(8.dp))
                        OutlinedButton(onClick = { vm.loadRecent() }) { Text("Retry") }
                    }
                }
                ui.books.isEmpty() -> CenterBox { Text("No books found.") }
                else -> LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    items(ui.books, key = { it.id }) { book ->
                        BookRow(
                            book = book,
                            coverModel = book.coverPath?.let { app.opdsClient.absoluteUrl(it) },
                            onClick = { selected = book },
                        )
                    }
                }
            }
        }
    }

    selected?.let { book ->
        ModalBottomSheet(
            onDismissRequest = { selected = null },
            sheetState = sheetState,
        ) {
            BookDetailSheet(
                book = book,
                coverModel = book.coverPath?.let { app.opdsClient.absoluteUrl(it) },
                isDownloaded = { fmt -> downloaded.any { it.id == book.id && it.format.equals(fmt, true) } },
                progressOf = { fmt -> progress[LibraryViewModel.keyOf(book.id, fmt)] },
                onDownload = { fmt -> vm.download(book, fmt) },
                onRemove = { fmt -> vm.remove(book.id, fmt) },
                onRead = { fmt ->
                    selected = null
                    onOpenReader(book.id, fmt.lowercase(), fmt.equals("pdf", true))
                },
            )
        }
    }
}

@Composable
private fun BookRow(book: OpdsBook, coverModel: Any?, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        BookCover(
            model = coverModel,
            title = book.title,
            modifier = Modifier
                .width(52.dp)
                .aspectRatio(0.66f),
        )
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                book.title,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            if (book.authors.isNotEmpty()) {
                Text(
                    book.authorLine,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun BookDetailSheet(
    book: OpdsBook,
    coverModel: Any?,
    isDownloaded: (String) -> Boolean,
    progressOf: (String) -> Int?,
    onDownload: (OpdsFormat) -> Unit,
    onRemove: (String) -> Unit,
    onRead: (String) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp)
            .padding(bottom = 32.dp),
    ) {
        Row {
            BookCover(
                model = coverModel,
                title = book.title,
                modifier = Modifier
                    .width(96.dp)
                    .aspectRatio(0.66f),
            )
            Spacer(Modifier.width(16.dp))
            Column {
                Text(book.title, style = MaterialTheme.typography.titleLarge)
                Spacer(Modifier.height(4.dp))
                Text(
                    book.authorLine,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        val readable = book.formats.filter { it.isReadable }
        Spacer(Modifier.height(16.dp))
        if (readable.isEmpty()) {
            Text(
                "No EPUB or PDF format available for this book.",
                style = MaterialTheme.typography.bodyMedium,
            )
        } else {
            Text("Formats", style = MaterialTheme.typography.titleMedium)
            readable.forEach { format ->
                FormatRow(
                    format = format,
                    downloaded = isDownloaded(format.format),
                    progress = progressOf(format.format),
                    onDownload = { onDownload(format) },
                    onRemove = { onRemove(format.format.lowercase()) },
                    onRead = { onRead(format.format) },
                )
            }
        }

        if (book.summary.isNotBlank()) {
            Spacer(Modifier.height(16.dp))
            Text("About", style = MaterialTheme.typography.titleMedium)
            Text(
                book.summary,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 8,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun FormatRow(
    format: OpdsFormat,
    downloaded: Boolean,
    progress: Int?,
    onDownload: () -> Unit,
    onRemove: () -> Unit,
    onRead: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                format.format + "  ·  " + formatBytes(format.sizeBytes),
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium,
            )
            when {
                progress != null -> {
                    Spacer(Modifier.height(4.dp))
                    LinearProgressIndicator(
                        progress = progress / 100f,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                downloaded -> Text(
                    "Available offline",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
        Spacer(Modifier.width(12.dp))
        when {
            progress != null -> Text("$progress%")
            downloaded -> Row {
                OutlinedButton(onClick = onRemove) { Text("Remove") }
                Spacer(Modifier.width(8.dp))
                Button(onClick = onRead) {
                    Icon(Icons.Filled.Check, contentDescription = null, modifier = Modifier.width(18.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Read")
                }
            }
            else -> Button(onClick = onDownload) { Text("Download") }
        }
    }
}

@Composable
private fun CenterBox(content: @Composable () -> Unit) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { content() }
}
