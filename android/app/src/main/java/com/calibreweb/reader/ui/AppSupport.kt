package com.calibreweb.reader.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.calibreweb.reader.CalibreApp

/** Retrieves the [CalibreApp] singleton from Compose. */
@Composable
fun rememberApp(): CalibreApp = LocalContext.current.applicationContext as CalibreApp

/** Builds a ViewModel that needs access to the app-scoped singletons. */
@Composable
inline fun <reified VM : ViewModel> appViewModel(
    crossinline create: (CalibreApp) -> VM,
): VM {
    val app = LocalContext.current.applicationContext as CalibreApp
    return viewModel(factory = viewModelFactory { initializer { create(app) } })
}
