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
     @param {string} filepath path of the current file, also part of the CFI, e.g. here: #epubcfi(/6/2[titlepage]!/4/1:0) it would be "titlepage"
     */
    getPreviousFilesSize(filepath) {
        let currentFile=this.getIdRef(filepath);
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

    getIdRef(filepath){
        return this.opfXml.querySelector(`[href="${filepath}"]`).getAttribute("id");
    }
    /**
     * resolves the given cfi to the xml node it points to
     * @param {string} cfistr epub-cfi string in the form: epubcfi(/6/16[id13]!/4[id2]/4/2[doc12]/1:0)
     * @return object with attributes "node" and "offset"
     */
    cfiToXmlNode(cfistr) {
        let cfi = new CFI(cfistr);
        let cfiPath = cfistr.split("(")[1].split(")")[0];
        let fileId = cfiPath.split("!")[0].split("[")[1].split("]")[0];
        return cfi.resolveLast(this.parser.parseFromString(this.decompress(this.resolveIDref(fileId)),"text/xml"));
    }

    /**
     takes the node that the cfi points at and counts the bytes of all nodes before that
     */
    getCurrentFileProgress(CFI) {
        let parse=this.cfiToXmlNode(CFI);
        let size=parse.offset;
        let startnode =  parse.node//returns text node
        let xmlnsLength = startnode.parentNode.namespaceURI.length;
        let prev = startnode.parentNode.previousElementSibling;
        while (prev !== null) {
            size += this.encoder.encode(prev.outerHTML).length - xmlnsLength;
            prev = prev.previousElementSibling;
        }
        let parent = startnode.parentElement.parentElement;
        while (parent !== null) {
            let parentPrev = parent.previousElementSibling;
            while (parentPrev !== null) {
                size += this.encoder.encode(parentPrev.outerHTML).length - xmlnsLength;
                parentPrev = parentPrev.previousElementSibling;
            }
            parent = parent.parentElement;
        }
        return size;
    }

    /**
     * @param currentFile filepath
     * @param CFI
     * @return {number} percentage as decimal
     */
    getProgress(currentFile, CFI) {
        let percentage = (this.getPreviousFilesSize(currentFile) + this.getCurrentFileProgress(CFI))/this.getTotalByteLength();
        if (percentage === Infinity) {
            return 0;
        } else if (percentage>1){
            return 1;
        }
        else{
            return percentage;
        }
    }
}

//wait until variable is assigned a value
function waitFor(variable, callback) {
  const interval = setInterval(function() {
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
    return Math.round(epubParser.getProgress(data.href,data.cfi)*100);
}

// register new event emitter locationchange that fires on urlchange
// source: https://stackoverflow.com/a/52809105/21941129
(() => {
    let oldPushState = history.pushState;
    history.pushState = function pushState() {
        let ret = oldPushState.apply(this, arguments);
        window.dispatchEvent(new Event('locationchange'));
        return ret;
    };

    let oldReplaceState = history.replaceState;
    history.replaceState = function replaceState() {
        let ret = oldReplaceState.apply(this, arguments);
        window.dispatchEvent(new Event('locationchange'));
        return ret;
    };

    window.addEventListener('popstate', () => {
        window.dispatchEvent(new Event('locationchange'));
    });
})();

var epubParser;
waitFor(reader.book,()=>{
    epubParser = new EpubParser(reader.book.archive.zip.files);
});
let progressDiv=document.getElementById("progress");

window.addEventListener('locationchange',()=>{
    let newPos=calculateProgress();
    progressDiv.textContent=newPos+"%";
});
