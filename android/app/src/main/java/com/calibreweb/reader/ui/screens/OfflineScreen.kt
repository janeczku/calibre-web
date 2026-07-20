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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.calibreweb.reader.data.DownloadedBook
import com.calibreweb.reader.ui.components.BookCover
import com.calibreweb.reader.ui.formatBytes
import com.calibreweb.reader.ui.rememberApp
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OfflineScreen(
    onOpenReader: (id: String, format: String, isPdf: Boolean) -> Unit,
) {
    val app = rememberApp()
    val scope = rememberCoroutineScope()
    val books by app.library.books.collectAsStateWithLifecycle()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Offline Books") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 12.dp),
        ) {
            if (books.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        "No books downloaded yet.\nOpen a book in Browse and tap Download.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                val total = books.sumOf { it.sizeBytes }
                Text(
                    "${books.size} book(s) · ${formatBytes(total)} used",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 8.dp),
                )
                LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(books, key = { it.id + "." + it.format }) { book ->
                        OfflineRow(
                            book = book,
                            coverModel = app.library.coverFile(book),
                            onOpen = {
                                onOpenReader(book.id, book.format, book.isPdf)
                            },
                            onDelete = { scope.launch { app.library.remove(book) } },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun OfflineRow(
    book: DownloadedBook,
    coverModel: Any?,
    onOpen: () -> Unit,
    onDelete: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onOpen)
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
            Text(
                book.authors,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                book.format.uppercase() + " · " + formatBytes(book.sizeBytes) +
                    if (book.progressPercent > 0) " · ${book.progressPercent}% read" else "",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (book.progressPercent in 1..99) {
                Spacer(Modifier.height(4.dp))
                LinearProgressIndicator(
                    progress = book.progressPercent / 100f,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp),
                )
            }
        }
        IconButton(onClick = onDelete) {
            Icon(Icons.Filled.Delete, contentDescription = "Remove download")
        }
    }
}
