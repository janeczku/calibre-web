package com.calibreweb.reader.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.calibreweb.reader.reader.epub.EpubReaderScreen
import com.calibreweb.reader.reader.pdf.PdfReaderScreen
import com.calibreweb.reader.ui.screens.BrowseScreen
import com.calibreweb.reader.ui.screens.OfflineScreen
import com.calibreweb.reader.ui.screens.SettingsScreen

object Routes {
    const val BROWSE = "browse"
    const val OFFLINE = "offline"
    const val SETTINGS = "settings"
    const val EPUB = "epub/{id}/{format}"
    const val PDF = "pdf/{id}/{format}"

    fun epub(id: String, format: String) = "epub/$id/$format"
    fun pdf(id: String, format: String) = "pdf/$id/$format"
}

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab(Routes.BROWSE, "Browse", Icons.Filled.Search),
    Tab(Routes.OFFLINE, "Offline", Icons.Filled.Download),
    Tab(Routes.SETTINGS, "Settings", Icons.Filled.Settings),
)

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    val app = rememberApp()
    val start = if (app.settings.isConfigured) Routes.BROWSE else Routes.SETTINGS

    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val showBottomBar = currentRoute in tabs.map { it.route }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = currentRoute == tab.route,
                            onClick = {
                                if (currentRoute != tab.route) {
                                    navController.navigate(tab.route) {
                                        popUpTo(navController.graph.findStartDestination().id) {
                                            saveState = true
                                        }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = start,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.BROWSE) {
                BrowseScreen(
                    onOpenReader = { id, format, isPdf ->
                        navController.navigate(
                            if (isPdf) Routes.pdf(id, format) else Routes.epub(id, format)
                        )
                    },
                    onNeedsSetup = { navController.navigate(Routes.SETTINGS) },
                )
            }
            composable(Routes.OFFLINE) {
                OfflineScreen(
                    onOpenReader = { id, format, isPdf ->
                        navController.navigate(
                            if (isPdf) Routes.pdf(id, format) else Routes.epub(id, format)
                        )
                    },
                )
            }
            composable(Routes.SETTINGS) {
                SettingsScreen(onSaved = {
                    navController.navigate(Routes.BROWSE) {
                        popUpTo(Routes.SETTINGS) { inclusive = true }
                    }
                })
            }
            composable(
                Routes.EPUB,
                arguments = listOf(
                    navArgument("id") { type = NavType.StringType },
                    navArgument("format") { type = NavType.StringType },
                ),
            ) { entry ->
                EpubReaderScreen(
                    bookId = entry.arguments?.getString("id").orEmpty(),
                    format = entry.arguments?.getString("format").orEmpty(),
                    onBack = { navController.popBackStack() },
                )
            }
            composable(
                Routes.PDF,
                arguments = listOf(
                    navArgument("id") { type = NavType.StringType },
                    navArgument("format") { type = NavType.StringType },
                ),
            ) { entry ->
                PdfReaderScreen(
                    bookId = entry.arguments?.getString("id").orEmpty(),
                    format = entry.arguments?.getString("format").orEmpty(),
                    onBack = { navController.popBackStack() },
                )
            }
        }
    }
}
