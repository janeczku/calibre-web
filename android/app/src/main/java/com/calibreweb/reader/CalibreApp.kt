package com.calibreweb.reader

import android.app.Application
import coil.ImageLoader
import coil.ImageLoaderFactory
import com.calibreweb.reader.data.KeyChainKeyManager
import com.calibreweb.reader.data.LibraryRepository
import com.calibreweb.reader.data.OpdsClient
import com.calibreweb.reader.data.SettingsStore

/**
 * Application-scoped singletons. Kept deliberately small (no DI framework) so
 * the whole graph is easy to follow.
 */
class CalibreApp : Application(), ImageLoaderFactory {

    lateinit var settings: SettingsStore
        private set
    lateinit var opdsClient: OpdsClient
        private set
    lateinit var library: LibraryRepository
        private set

    override fun onCreate() {
        super.onCreate()
        settings = SettingsStore(this)
        opdsClient = OpdsClient(settings, KeyChainKeyManager(this) { settings.clientCertificateAlias })
        library = LibraryRepository(this, opdsClient)
    }

    /** Coil loads covers through the same authenticated OkHttp client. */
    override fun newImageLoader(): ImageLoader =
        ImageLoader.Builder(this)
            .okHttpClient(opdsClient.httpClient)
            .crossfade(true)
            .build()

    companion object {
        fun from(app: Application): CalibreApp = app as CalibreApp
    }
}
