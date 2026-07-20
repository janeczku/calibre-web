package com.calibreweb.reader.reader.epub

import android.util.Xml
import org.xmlpull.v1.XmlPullParser
import java.io.File
import java.io.IOException
import java.net.URLDecoder
import java.util.zip.ZipInputStream

/**
 * A minimal EPUB model: unzips the container and resolves the spine (reading
 * order) into a list of local HTML/XHTML files that can be shown in a WebView.
 */
class EpubBook private constructor(
    val title: String?,
    val spineFiles: List<File>,
) {
    companion object {

        fun open(epubFile: File, extractDir: File): EpubBook {
            val container = File(extractDir, "META-INF/container.xml")
            if (!container.exists()) {
                extractDir.mkdirs()
                unzip(epubFile, extractDir)
            }
            val opfPath = parseContainer(container)
                ?: throw IOException("Invalid EPUB: no OPF declared in container.xml")
            val opfFile = File(extractDir, opfPath)
            if (!opfFile.exists()) throw IOException("Invalid EPUB: missing $opfPath")
            val opfDir = opfFile.parentFile ?: extractDir

            val (title, hrefs) = parseOpf(opfFile)
            val spineFiles = hrefs.mapNotNull { href ->
                val decoded = runCatching { URLDecoder.decode(href, "UTF-8") }.getOrDefault(href)
                File(opfDir, decoded).takeIf { it.exists() }
            }
            if (spineFiles.isEmpty()) throw IOException("EPUB has no readable content")
            return EpubBook(title, spineFiles)
        }

        private fun unzip(zip: File, dest: File) {
            val destCanonical = dest.canonicalPath
            ZipInputStream(zip.inputStream().buffered()).use { zis ->
                var entry = zis.nextEntry
                while (entry != null) {
                    val outFile = File(dest, entry.name)
                    // Zip-slip protection
                    if (!outFile.canonicalPath.startsWith(destCanonical + File.separator)) {
                        throw IOException("Unsafe zip entry: ${entry.name}")
                    }
                    if (entry.isDirectory) {
                        outFile.mkdirs()
                    } else {
                        outFile.parentFile?.mkdirs()
                        outFile.outputStream().use { zis.copyTo(it) }
                    }
                    zis.closeEntry()
                    entry = zis.nextEntry
                }
            }
        }

        private fun parseContainer(container: File): String? {
            container.inputStream().use { input ->
                val parser = newParser(input)
                var event = parser.eventType
                while (event != XmlPullParser.END_DOCUMENT) {
                    if (event == XmlPullParser.START_TAG && parser.name == "rootfile") {
                        parser.getAttributeValue(null, "full-path")?.let { return it }
                    }
                    event = parser.next()
                }
            }
            return null
        }

        private fun parseOpf(opf: File): Pair<String?, List<String>> {
            val manifest = HashMap<String, String>()
            val spine = ArrayList<String>()
            var title: String? = null
            var inTitle = false

            opf.inputStream().use { input ->
                val parser = newParser(input)
                var event = parser.eventType
                while (event != XmlPullParser.END_DOCUMENT) {
                    when (event) {
                        XmlPullParser.START_TAG -> when (parser.name) {
                            "item" -> {
                                val id = parser.getAttributeValue(null, "id")
                                val href = parser.getAttributeValue(null, "href")
                                if (id != null && href != null) manifest[id] = href
                            }
                            "itemref" -> parser.getAttributeValue(null, "idref")?.let { spine.add(it) }
                            "title", "dc:title" -> inTitle = true
                        }
                        XmlPullParser.TEXT -> if (inTitle && title == null) title = parser.text?.trim()
                        XmlPullParser.END_TAG -> if (parser.name == "title" || parser.name == "dc:title") {
                            inTitle = false
                        }
                    }
                    event = parser.next()
                }
            }
            val hrefs = spine.mapNotNull { manifest[it] }
            return title to hrefs
        }

        private fun newParser(input: java.io.InputStream): XmlPullParser {
            val parser = Xml.newPullParser()
            parser.setFeature(XmlPullParser.FEATURE_PROCESS_NAMESPACES, false)
            parser.setInput(input, null)
            return parser
        }
    }
}
