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
                // console.log(file.name + " " + file._data.uncompressedSize)
                size += file._data.uncompressedSize;
            }
        }
        return size;
    }

    /**
     * gets file from files and returns decompressed content as string
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
        return this.absPath(this.opfXml.getElementById(idref).getAttribute("href"));
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
                let filepath = this.resolveIDref(file);
                //ignore non text files
                if (filepath.endsWith("html")) {
                    // console.log(filepath + " " + bytesize)
                    bytesize += this.files[filepath]._data.uncompressedSize;
                }
            } else {
                break;
            }
        }
        return bytesize;
    }

    /**
     * resolves the given cfi to the xml node it points to
     * @param {string} cfi epub-cfi string in the form: epubcfi(/6/16[id13]!/4[id2]/4/2[doc12]/1:0)
     * @return XML Text-Node
     */
    cfiToXmlNode(cfi) {
        let cfiPath = cfi.split("(")[1].split(")")[0];
        let fileId = cfiPath.split("!")[0].split("[")[1].split("]")[0];
        let xml = this.parser.parseFromString(this.decompress(this.resolveIDref(fileId)), "text/xml");
        let components = cfiPath.split("!")[1].split("/").slice(1);
        let currentNode = xml.getElementsByTagName("html")[0];
        for (const component of components) {
            this.validateChildNodes(currentNode);
            // console.log(currentNode);
            // console.log(component);
            let index = 0;
            if (component.includes("[")) {
                index = parseInt(component.split("[")[0]) - 1;
                currentNode = currentNode.childNodes[index];
                console.assert(currentNode.getAttribute("id") === component.split("[")[1].split("]")[0], "failed to resolve node");
            } else if (component.includes(":")) {
                index = component.split(":")[0] - 1;
                return currentNode.childNodes[index]; //exit point
            } else {
                index = parseInt(component);
                currentNode = currentNode.childNodes[index - 1];
            }
        }
    }

    /**
     * inserts missing text/element nodes to keep them alternating
     * @param {*} parentNode
     */
    validateChildNodes(parentNode) {
        for (let index = 0; index < parentNode.childNodes.length;) {
            const element = parentNode.childNodes[index];
            if (index % 2 === 0 && element.nodeType === 1) {
                element.parentNode.insertBefore(parentNode.ownerDocument.createTextNode(""), element);
                continue;
            }
            if (index % 2 === 1 && element.nodeType === 3) {
                element.insertBefore(parentNode.ownerDocument.createElement("")); //TODO check
                continue;
            }
            index++;
        }

    }

    /**
     takes the node that the cfi points at and counts the bytes of all nodes before that
     */
    getCurrentFileProgress(CFI) {
        let size = parseInt(CFI.split(":")[1])//text offset in node
        let startnode = this.cfiToXmlNode(CFI); //returns text node
        let xmlnsLength = startnode.parentNode.namespaceURI.length;
        let prev = startnode.parentNode.previousElementSibling;
        while (prev !== null) {
            // console.log("size: "+size)
            // console.log(prev.outerHTML)
            // console.log(this.encoder.encode(prev.outerHTML).length - xmlnsLength)
            size += this.encoder.encode(prev.outerHTML).length - xmlnsLength;
            prev = prev.previousElementSibling;
        }
        let parent = startnode.parentElement.parentElement;
        while (parent !== null) {
            let parentPrev = parent.previousElementSibling;
            while (parentPrev !== null) {
                // console.log(parentPrev.outerHTML)
                // console.log(this.encoder.encode(parentPrev.outerHTML).length - xmlnsLength)

                size += this.encoder.encode(parentPrev.outerHTML).length - xmlnsLength;
                parentPrev = parentPrev.previousElementSibling;
            }
            parent = parent.parentElement;
        }
        return size;
    }

    getProgress(currentFile, CFI) {
        let percentage = (this.getPreviousFilesSize(currentFile) + this.getCurrentFileProgress(CFI))/this.getTotalByteLength();
        if (percentage === Infinity) {
            return 0;
        } else {
            return percentage;
        }
    }
}
function waitFor(variable, callback) {
  var interval = setInterval(function() {
    if (variable!==undefined) {
      clearInterval(interval);
      callback();
    }
  }, 200);
}

/**
 * returns progress percentage
 * @return {number}
 */
function calculateProgress(){
    let data=reader.rendition.currentLocation().end;
    return epubParser.getProgress(epubParser.absPath(data.href),data.cfi).toFixed(2)*100;
}
var epubParser;
waitFor(reader.book,()=>{
    epubParser = new EpubParser(reader.book.archive.zip.files);
})

window.addEventListener('hashchange',()=>{console.log("test")})
/*
document.getElementById("next").addEventListener('click',calculateProgress);
document.getElementById("prev").addEventListener('click',calculateProgress);
*/
