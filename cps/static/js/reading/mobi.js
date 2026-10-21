import "../libs/foliate/view.js"
import { isMOBI, MOBI } from "../libs/foliate/mobi.js"
import { unzlibSync } from "../libs/foliate/vendor/fflate.js"

const body = document.body
const bookFormat = body.dataset.bookFormat
const bookUrl = body.dataset.bookUrl

const viewContainer = document.getElementById("view-container")
const status = document.getElementById("status")
const chapterTitle = document.getElementById("chapter-title")
const tocPanel = document.getElementById("toc")
const tocNav = document.getElementById("toc-nav")
const tocToggle = document.getElementById("toc-toggle")
const tocBackdrop = document.getElementById("toc-backdrop")
const progressSlider = document.getElementById("progress-slider")
const progressLabel = document.getElementById("progress-label")
const prevButton = document.getElementById("prev-page")
const nextButton = document.getElementById("next-page")

const readerStyles = `
    @namespace epub "http://www.idpf.org/2007/ops";
    html {
        color-scheme: light dark;
    }
    body {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
        line-height: 1.6;
        overflow-wrap: break-word;
    }
    p, li, blockquote, dd {
        line-height: 1.6;
        text-align: justify;
        hyphens: auto;
        -webkit-hyphens: auto;
    }
    pre {
        white-space: pre-wrap !important;
    }
    img, svg, video {
        max-width: 100% !important;
        height: auto !important;
    }
    a {
        color: #2b6cb0;
    }
    @media (prefers-color-scheme: dark) {
        a {
            color: #7fb3e8;
        }
    }
`

const view = document.createElement("foliate-view")
viewContainer.append(view)

function showError(message) {
    status.hidden = false
    status.classList.add("error")
    status.replaceChildren()

    const paragraph = document.createElement("p")
    paragraph.textContent = message
    const backLink = document.createElement("a")
    backLink.className = "button"
    backLink.href = body.dataset.backUrl
    backLink.textContent = body.dataset.backLabel
    status.append(paragraph, backLink)
}

function setTOCOpen(open) {
    tocPanel.classList.toggle("open", open)
    tocBackdrop.classList.toggle("open", open)
    tocPanel.setAttribute("aria-hidden", String(!open))
    tocToggle.setAttribute("aria-expanded", String(open))
}

function buildTOC(items, parent = tocNav) {
    if (!items?.length) return
    const list = document.createElement("ul")
    for (const item of items) {
        if (!item.href) continue
        const entry = document.createElement("li")
        const link = document.createElement("a")
        link.href = "#"
        link.textContent = item.label || "—"
        link.addEventListener("click", event => {
            event.preventDefault()
            view.goTo(item.href).catch(error => console.error(error))
            setTOCOpen(false)
        })
        entry.append(link)
        if (item.subitems?.length) buildTOC(item.subitems, entry)
        list.append(entry)
    }
    parent.append(list)
}

function updateProgress({ detail }) {
    const { fraction, tocItem } = detail
    if (Number.isFinite(fraction)) {
        progressSlider.value = String(fraction)
        progressLabel.textContent = `${Math.round(fraction * 100)}%`
    }
    if (tocItem?.label) chapterTitle.textContent = tocItem.label
}

function handleKeydown(event) {
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return
    switch (event.key) {
        case "ArrowLeft":
        case "PageUp":
            event.preventDefault()
            view.goLeft()
            break
        case "ArrowRight":
        case "PageDown":
        case " ":
            event.preventDefault()
            view.goRight()
            break
        case "Home":
            event.preventDefault()
            view.goToFraction(0)
            break
        case "End":
            event.preventDefault()
            view.goToFraction(1)
            break
        case "Escape":
            setTOCOpen(false)
            break
    }
}

async function loadBook() {
    const response = await fetch(bookUrl, { credentials: "same-origin" })
    if (!response.ok) {
        throw new Error(`${body.dataset.errorLoading} (${response.status} ${response.statusText})`)
    }

    const blob = await response.blob()
    const file = new File([blob], `book.${bookFormat}`, {
        type: blob.type || "application/x-mobipocket-ebook",
    })
    if (!(await isMOBI(file))) {
        throw new Error(body.dataset.errorUnsupported)
    }

    const book = await new MOBI({ unzlib: unzlibSync }).open(file)
    await view.open(book)
    view.renderer.setStyles?.(readerStyles)
    buildTOC(book.toc)
    await view.renderer.next()
    status.hidden = true
}

tocToggle.addEventListener("click", () => setTOCOpen(!tocPanel.classList.contains("open")))
tocBackdrop.addEventListener("click", () => setTOCOpen(false))
progressSlider.addEventListener("change", () => view.goToFraction(Number(progressSlider.value)))
prevButton.addEventListener("click", () => view.goLeft())
nextButton.addEventListener("click", () => view.goRight())

view.addEventListener("relocate", updateProgress)
view.addEventListener("load", ({ detail: { doc } }) => doc.addEventListener("keydown", handleKeydown))
view.addEventListener("external-link", event => {
    // Only allow normal web/mail links from inside the book
    if (!/^(https?:|mailto:)/i.test(event.detail.href_)) event.preventDefault()
})
document.addEventListener("keydown", handleKeydown)

loadBook().catch(error => {
    console.error(error)
    showError(error.message || body.dataset.errorLoading)
})
