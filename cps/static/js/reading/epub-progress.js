class EpubParser {
    constructor(filesList) {
        this.files = filesList;
        this.parser = new DOMParser();
        this.opfXml = this.getOPFXml();
        this.encoder = new TextEncoder();
    }


    getTotalByteLength() {
        let size = 0;
        for (let key of Object.keys(this.files)) {
            let file = this.files[key];
            if (file.name.endsWith("html")) {
                console.log(file.name + " " + file._data.uncompressedSize)
                size += file._data.uncompressedSize;
            }
        }
        return size;
    }

    /**
     * @param {string} filename name of the file in filelist
     * @return {string} string representation of decompressed bytes
     */
    decompress(filename) {
        return pako.inflate(this.files[filename]._data.compressedContent, {raw: true, to: "string"});
    }

    getOPFXml() {
        let content = this.decompress("META-INF/container.xml");
        let xml = this.parser.parseFromString(content, "text/xml");
        let path = xml.getElementsByTagName("rootfile")[0].getAttribute("full-path");
        this.opfDir = path.split("/").slice(0, -1).join("/");
        return this.parser.parseFromString(this.decompress(path), "text/xml");
    }


    getSpine() {
        return Array.from(this.opfXml.getElementsByTagName("spine")[0].children).map(node => node.getAttribute("idref"));
    }

    /**
     resolves an idref in content.opf to its file
     */
    resolveIDref(idref) {
        return this.opfXml.getElementById(idref).getAttribute("href");
    }

    /**
     * returns absolute path from path relative to content.opf
     * @param path
     */
    absPath(path) {
        if (this.opfDir) {
            return [this.opfDir, path].join("/");
        } else {
            return path;
        }
    }

    /**
     returns the sum of the bytesize of all html files that are located before it in the spine
     @param {string} currentFile idref of the current file, also part of the CFI, e.g. here: #epubcfi(/6/2[titlepage]!/4/1:0) it would be "titlepage"
     */
    getPreviousFilesSize(currentFile) {
        let bytesize = 0;
        for (let file of this.getSpine()) {
            if (file !== currentFile) {
                let filepath = this.absPath(this.resolveIDref(file));
                //ignore non text files
                if (filepath.endsWith("html")) {
                    console.log(filepath + " " + bytesize)
                    bytesize += this.files[filepath]._data.uncompressedSize;
                }
            } else {
                break;
            }
        }
        return bytesize;
    }
    cfiToXmlNode(file,cfi){

    }
    /**
    takes the node that the cfi points at and counts the bytes of all nodes before that
     */
    getCurrentFileProgress(currentFile, CFI) {
        let size = 0
        let startnode = this.cfiToXmlNode(currentFile,CFI);
        let prev = startnode.previousElementSibling;
        while (prev !== null) {
            size += this.encoder.encode(prev.outerHTML).length;
            prev = prev.previousElementSibling;
        }
        let parent = startnode.parentElement;
        while (parent !== null) {
            let parentPrev = parent.previousElementSibling;
            while (parentPrev !== null) {
                size += this.encoder.encode(parentPrev.outerHTML).length;
                parentPrev = parentPrev.previousElementSibling;
            }
            parent=parent.parentElement;
        }
        return size;
    }

    getProgress(currentFile, CFI) {
        let percentage = this.getTotalByteLength() / (this.getPreviousFilesSize(currentFile) + this.getCurrentFileProgress(currentFile, CFI));
        if (percentage === Infinity) {
            return 0;
        } else {
            return percentage;
        }
    }
}
