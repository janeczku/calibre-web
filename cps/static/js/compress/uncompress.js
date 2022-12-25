// Copyright (c) 2017 Matthew Brennan Jones <matthew.brennan.jones@gmail.com>
// This software is licensed under a MIT License
// https://github.com/workhorsy/uncompress.js

"use strict";


function loadScript(url, cb) {
	// Window
	if (typeof window === 'object') {
		let script = document.createElement('script');
		script.type = "text/javascript";
		script.src = url;
		script.onload = function() {
			if (cb) cb();
		};
		document.head.appendChild(script);
	// Web Worker
	} else if (typeof importScripts === 'function') {
		importScripts(url);
		if (cb) cb();
	}
}

function currentScriptPath() {
	// NOTE: document.currentScript does not work in a Web Worker
	// So we have to parse a stack trace maually
	try {
		throw new Error('');
	} catch(e) {
		let stack = e.stack;
		let line = null;

		// Chrome and IE
		if (stack.indexOf('@') !== -1) {
			line = stack.split('@')[1].split('\n')[0];
		// Firefox
		} else {
			line = stack.split('(')[1].split(')')[0];
		}
		line = line.substring(0, line.lastIndexOf('/')) + '/';
		return line;
	}
}

// This is used by libunrar.js to load libunrar.js.mem
let unrarMemoryFileLocation = null;
let g_on_loaded_cb = null;

(function() {

let _loaded_archive_formats = [];

// Polyfill for missing array slice method (IE 11)
if (typeof Uint8Array !== 'undefined') {
if (! Uint8Array.prototype.slice) {
	Uint8Array.prototype.slice = function(start, end) {
		let retval = new Uint8Array(end - start);
		let j = 0;
		for (let i=start; i<end; ++i) {
			retval[j] = this[i];
			j++;
		}
		return retval;
	};
}
}

// FIXME: This function is super inefficient
function saneJoin(array, separator) {
	let retval = '';
	for (let i=0; i<array.length; ++i) {
		if (i === 0) {
			retval += array[i];
		} else {
			retval += separator + array[i];
		}
	}
	return retval;
}

function saneMap(array, cb) {
	let retval = new Array(array.length);
	for (let i=0; i<retval.length; ++i) {
		retval[i] = cb(array[i]);
	}
	return retval;
}

function loadArchiveFormats(formats, cb) {
	// Get the path of the current script
	let path = currentScriptPath();
	let load_counter = 0;

	let checkForLoadDone = function() {
		load_counter++;

		// Get the total number of loads before we are done loading
		// If loading RAR in a Window, have 1 extra load.
		let load_total = formats.length;
		if (formats.indexOf('rar') !== -1 && typeof window === 'object') {
			load_total++;
		}

		// run the callback if the last script has loaded
		if (load_counter === load_total) {
			cb();
		}
	};

	g_on_loaded_cb = checkForLoadDone;

	// Load the formats
	formats.forEach(function(archive_format) {
		// Skip this format if it is already loaded
		if (_loaded_archive_formats.indexOf(archive_format) !== -1) {
			return;
		}

		// Load the archive format
		switch (archive_format) {
			case 'rar':
				unrarMemoryFileLocation = path + 'libunrar.js.mem';
				loadScript(path + 'libunrar.js', checkForLoadDone);
				_loaded_archive_formats.push(archive_format);
				break;
			case 'zip':
				loadScript(path + 'jszip.min.js', checkForLoadDone);
				_loaded_archive_formats.push(archive_format);
				break;
			case 'tar':
				loadScript(path + 'libuntar.js', checkForLoadDone);
				_loaded_archive_formats.push(archive_format);
				break;
			default:
				throw new Error("Unknown archive format '" + archive_format + "'.");
		}
	});
}

function archiveOpenFile(array_buffer, cb) {
	let file_name = "Hugo"; //file.name;
	let password = null;

    try {
        let archive = archiveOpenArrayBuffer(file_name, password, array_buffer);
        cb(archive, null);
    } catch(e) {
        cb(null, e);
    }
}

function archiveOpenArrayBuffer(file_name, password, array_buffer) {
	// Get the archive type
	let archive_type = null;
	if (isRarFile(array_buffer)) {
		archive_type = 'rar';
	} else if(isZipFile(array_buffer)) {
		archive_type = 'zip';
	} else if(isTarFile(array_buffer)) {
		archive_type = 'tar';
	} else {
		throw new Error("The archive type is unknown");
	}

	// Make sure the archive format is loaded
	if (_loaded_archive_formats.indexOf(archive_type) === -1) {
		throw new Error("The archive format '" + archive_type + "' is not loaded.");
	}

	// Get the entries
	let handle = null;
	let entries = [];
	try {
		switch (archive_type) {
			case 'rar':
				handle = _rarOpen(file_name, password, array_buffer);
				entries = _rarGetEntries(handle);
				break;
			case 'zip':
				handle = _zipOpen(file_name, password, array_buffer);
				entries = _zipGetEntries(handle);
				break;
			case 'tar':
				handle = _tarOpen(file_name, password, array_buffer);
				entries = _tarGetEntries(handle);
				break;
		}
	} catch(e) {
		throw new Error("Failed to open '" + archive_type + "' archive.");
	}

	// Sort the entries by name
	entries.sort(function(a, b) {
		if(a.name < b.name) return -1;
		if(a.name > b.name) return 1;
		return 0;
	});

	// Return the archive object
	return {
		file_name: file_name,
		archive_type: archive_type,
		array_buffer: array_buffer,
		entries: entries,
		handle: handle
	};
}

function archiveClose(archive) {
	archive.file_name = null;
	archive.archive_type = null;
	archive.array_buffer = null;
	archive.entries = null;
	archive.handle = null;
}

function _rarOpen(file_name, password, array_buffer) {
	// Create an array of rar files
	let rar_files = [{
		name: file_name,
		size: array_buffer.byteLength,
		type: '',
		content: new Uint8Array(array_buffer)
	}];

	// Return rar handle
	return {
		file_name: file_name,
		array_buffer: array_buffer,
		password: password,
		rar_files: rar_files
	};
}

function _zipOpen(file_name, password, array_buffer) {
	let zip = new JSZip(array_buffer);

	// Return zip handle
	return {
		file_name: file_name,
		array_buffer: array_buffer,
		password: password,
		zip: zip
	};
}

function _tarOpen(file_name, password, array_buffer) {
	// Return tar handle
	return {
		file_name: file_name,
		array_buffer: array_buffer,
		password: password
	};
}

function _rarGetEntries(rar_handle) {
	// Get the entries
	let info = readRARFileNames(rar_handle.rar_files, rar_handle.password);
	let entries = [];
	Object.keys(info).forEach(function(i) {
		let name = info[i].name;
		let is_file = info[i].is_file;
        if (is_file) {
            entries.push({
                name: name,
                is_file: is_file, // info[i].is_file,
                size_compressed: info[i].size_compressed,
                size_uncompressed: info[i].size_uncompressed,
                readData: function (cb) {
                    setTimeout(function () {
                        if (is_file) {
                            try {
                                readRARContent(rar_handle.rar_files, rar_handle.password, name, cb);
                            } catch (e) {
                                cb(null, e);
                            }
                        } else {
                            cb(null, null);
                        }
                    }, 0);
                }
            });
        }
	});

	return entries;
}

function _zipGetEntries(zip_handle) {
	let zip = zip_handle.zip;

	// Get all the entries
	let entries = [];
	Object.keys(zip.files).forEach(function(i) {
		let zip_entry = zip.files[i];
		let name = zip_entry.name;
		let is_file = ! zip_entry.dir;
		let size_compressed = zip_entry._data ? zip_entry._data.compressedSize : 0;
		let size_uncompressed = zip_entry._data ? zip_entry._data.uncompressedSize : 0;
        if (is_file) {
            entries.push({
                name: name,
                is_file: is_file,
                size_compressed: size_compressed,
                size_uncompressed: size_uncompressed,
                readData: function (cb) {
                    setTimeout(function () {
                        if (is_file) {
                            let data = zip_entry.asArrayBuffer();
                            cb(data, null);
                        } else {
                            cb(null, null);
                        }
                    }, 0);
                }
            });
        }
	});

	return entries;
}

function _tarGetEntries(tar_handle) {
	let tar_entries = tarGetEntries(tar_handle.file_name, tar_handle.array_buffer);

	// Get all the entries
	let entries = [];
	tar_entries.forEach(function(entry) {
		let name = entry.name;
		let is_file = entry.is_file;
		let size = entry.size;
        if (is_file) {
            entries.push({
                name: name,
                is_file: is_file,
                size_compressed: size,
                size_uncompressed: size,
                readData: function (cb) {
                    setTimeout(function () {
                        if (is_file) {
                            let data = tarGetEntryData(entry, tar_handle.array_buffer);
                            cb(data.buffer, null);
                        } else {
                            cb(null, null);
                        }
                    }, 0);
                }
            });
        }
	});

	return entries;
}

function isRarFile(array_buffer) {
	// The three styles of RAR headers
	let rar_header1 = saneJoin([0x52, 0x45, 0x7E, 0x5E], ', '); // old
	let rar_header2 = saneJoin([0x52, 0x61, 0x72, 0x21, 0x1A, 0x07, 0x00], ', '); // 1.5 to 4.0
	let rar_header3 = saneJoin([0x52, 0x61, 0x72, 0x21, 0x1A, 0x07, 0x01, 0x00], ', '); // 5.0

	// Just return false if the file is smaller than the header
	if (array_buffer.byteLength < 8) {
		return false;
	}

	// Return true if the header matches one of the RAR headers
	let header1 = saneJoin(new Uint8Array(array_buffer).slice(0, 4), ', ');
	let header2 = saneJoin(new Uint8Array(array_buffer).slice(0, 7), ', ');
	let header3 = saneJoin(new Uint8Array(array_buffer).slice(0, 8), ', ');
	return (header1 === rar_header1 || header2 === rar_header2 || header3 === rar_header3);
}

function isZipFile(array_buffer) {
	// The ZIP header
	let zip_header = saneJoin([0x50, 0x4b, 0x03, 0x04], ', ');

	// Just return false if the file is smaller than the header
	if (array_buffer.byteLength < 4) {
		return false;
	}

	// Return true if the header matches the ZIP header
	let header = saneJoin(new Uint8Array(array_buffer).slice(0, 4), ', ');
	return (header === zip_header);
}

function isTarFile(array_buffer) {
	// The TAR header
	let tar_header = saneJoin(['u', 's', 't', 'a', 'r'], ', ');

	// Just return false if the file is smaller than the header size
	if (array_buffer.byteLength < 512) {
		return false;
	}

	// Return true if the header matches the TAR header
	let header = saneJoin(saneMap(new Uint8Array(array_buffer).slice(257, 257 + 5), String.fromCharCode), ', ');
	return (header === tar_header);
}

// Figure out if we are running in a Window or Web Worker
let scope = null;
if (typeof window === 'object') {
	scope = window;
} else if (typeof importScripts === 'function') {
	scope = self;
}

// Set exports
scope.loadArchiveFormats = loadArchiveFormats;
scope.archiveOpenFile = archiveOpenFile;
scope.archiveOpenArrayBuffer = archiveOpenArrayBuffer;
scope.archiveClose = archiveClose;
scope.isRarFile = isRarFile;
scope.isZipFile = isZipFile;
scope.isTarFile = isTarFile;
scope.saneJoin = saneJoin;
scope.saneMap = saneMap;
})();
