app.bringToFront();

var startupArguments = (typeof arguments !== 'undefined') ? arguments : [];
var SUPPORTED_IMAGE_REGEX = /\.(arw|jpg|jpe|jpeg|dng|bmp|tif|tiff|psd|crw|cr2|exr|pcx|nef|dcr|dc2|erf|raf|orf|tga|mos|pef|png)$/i;

function main(args) {
    var folderPath = args && args.length > 0 ? args[0] : null;
    var outputFormat = args && args.length > 1 ? args[1] : "jpg";
    var outputFolder = args && args.length > 2 ? args[2] : null;

    try {
        return runFocusStacking(folderPath, outputFormat, outputFolder);
    } catch (e) {
        return "ERROR: " + getErrorText(e);
    }
}

function runFocusStacking(folderPath, outputFormat, outputFolder) {
    var mainFolder = resolveInputFolder(folderPath);
    if (!mainFolder) {
        return "Error: No folder selected";
    }

    var folders = getSubfolders(mainFolder);
    var processedFolders = 0;
    var failedFolders = [];

    for (var i = 0; i < folders.length; i++) {
        var currentFolder = folders[i];
        if (!(currentFolder instanceof Folder)) {
            continue;
        }

        try {
            $.writeln("Processing folder: " + currentFolder.fsName);
            if (processFolder(currentFolder, outputFolder, outputFormat)) {
                processedFolders++;
            } else {
                $.writeln("Skipped folder (not enough images or no valid files): " + currentFolder.fsName);
            }
        } catch (e) {
            failedFolders.push(currentFolder.name + ": " + getErrorText(e));
            $.writeln("Folder failed: " + currentFolder.fsName + " -> " + getErrorText(e));
            closeAllOpenDocuments();
        }
    }

    var result = "Success: Processed " + processedFolders + " folder(s) for focus stacking";
    if (failedFolders.length) {
        result += "; Failed " + failedFolders.length + " folder(s): " + failedFolders.join("; ");
    }
    return result;
}

function resolveInputFolder(folderPath) {
    if (folderPath) {
        var folder = new Folder(folderPath);
        if (!folder.exists) {
            alert("Folder does not exist: " + folderPath);
            return null;
        }
        return folder;
    }

    var selectedFolder = Folder.selectDialog("Please select the folder with folders to process");
    return selectedFolder;
}

function getSubfolders(rootFolder) {
    var items = rootFolder.getFiles();
    var folders = [];

    for (var i = 0; i < items.length; i++) {
        if (items[i] instanceof Folder) {
            folders.push(items[i]);
        }
    }

    return folders;
}

function processFolder(selectedFolder, outputFolder, outputFormat) {
    if (!selectedFolder) {
        return false;
    }

    if (outputFolder) {
        var outputFolderRef = new Folder(outputFolder);
        if (!outputFolderRef.exists) {
            outputFolderRef.create();
        }
        if (!outputFolderRef.exists) {
            $.writeln("ERROR: could not create output folder: " + outputFolderRef.fsName);
            return false;
        }
        outputFolder = outputFolderRef;
    } else {
        outputFolder = selectedFolder.parent;
    }

    $.writeln("Resolved output folder: " + outputFolder.fsName);
    closeAllOpenDocuments();

    var imageFiles = selectedFolder.getFiles(SUPPORTED_IMAGE_REGEX);
    if (!imageFiles || imageFiles.length < 2) {
        return false;
    }

    var stackFiles = [];
    for (var i = 0; i < imageFiles.length; i++) {
        stackFiles.push(imageFiles[i]);
    }

    try {
        loadImagesIntoStack(stackFiles);
        selectAllLayers();
        alignLayers();
        blendAlignedLayers();

        var baseName = getBaseName(selectedFolder.name);
        var extension = outputFormat && outputFormat.toLowerCase() === 'tiff16' ? 'tif' : 'jpg';
        var outputFile = new File(outputFolder.fsName + '/' + baseName + '_fs.' + extension);

        if (extension === 'tif') {
            saveAsTiff16(outputFile);
        } else {
            saveAsJpeg(outputFile);
        }

        app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        return true;
    } catch (e) {
        if (app.activeDocument) {
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        }
        throw e;
    }
}

function loadImagesIntoStack(files) {
    var scriptsFolder = decodeURI(app.path + '/' + localize('$$$/ScriptingSupport/InstalledScripts=Presets/Scripts'));
    loadLayersFromScript = true;
    $.evalFile(new File(scriptsFolder + '/Load Files into Stack.jsx'));
    loadLayers.intoStack(files);
}

function closeAllOpenDocuments() {
    while (app.documents.length > 0) {
        try {
            app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        } catch (e) {
            break;
        }
    }
}

function selectAllLayers() {
    var desc = new ActionDescriptor();
    var ref = new ActionReference();

    ref.putEnumerated(charIDToTypeID('Lyr '), charIDToTypeID('Ordn'), charIDToTypeID('Trgt'));
    desc.putReference(charIDToTypeID('null'), ref);

    executeAction(stringIDToTypeID('selectAllLayers'), desc, DialogModes.NO);
}

function alignLayers() {
    var desc = new ActionDescriptor();
    var ref = new ActionReference();

    ref.putEnumerated(charIDToTypeID('Lyr '), charIDToTypeID('Ordn'), charIDToTypeID('Trgt'));
    desc.putReference(charIDToTypeID('null'), ref);
    desc.putEnumerated(charIDToTypeID('Usng'), charIDToTypeID('ADSt'), stringIDToTypeID('ADSContent'));
    desc.putEnumerated(charIDToTypeID('Aply'), stringIDToTypeID('projection'), charIDToTypeID('Auto'));
    desc.putBoolean(stringIDToTypeID('vignette'), false);
    desc.putBoolean(stringIDToTypeID('radialDistort'), false);

    executeAction(charIDToTypeID('Algn'), desc, DialogModes.NO);
}

function blendAlignedLayers() {
    var desc = new ActionDescriptor();
    desc.putEnumerated(stringIDToTypeID('apply'), stringIDToTypeID('autoBlendType'), stringIDToTypeID('maxDOF'));
    desc.putBoolean(stringIDToTypeID('colorCorrection'), true);
    desc.putBoolean(stringIDToTypeID('autoTransparencyFill'), false);

    executeAction(stringIDToTypeID('mergeAlignedLayers'), desc, DialogModes.NO);
}

function saveAsJpeg(fileRef) {
    var jpgOptions = new JPEGSaveOptions();
    jpgOptions.quality = 12;
    jpgOptions.embedColorProfile = true;
    jpgOptions.formatOptions = FormatOptions.PROGRESSIVE;
    jpgOptions.scans = 5;
    jpgOptions.matte = MatteType.NONE;

    $.writeln("Saving JPEG to " + fileRef.fsName);
    activeDocument.saveAs(fileRef, jpgOptions, true, Extension.LOWERCASE);
    $.writeln("Saved JPEG: " + fileRef.fsName);
}

function saveAsTiff16(fileRef) {
    var tiffOptions = new TiffSaveOptions();
    tiffOptions.imageCompression = TIFFEncoding.NONE;
    tiffOptions.layers = false;
    tiffOptions.embedColorProfile = true;
    tiffOptions.alphaChannels = false;
    tiffOptions.byteOrder = ByteOrder.IBM;
    tiffOptions.saveImagePyramid = false;

    $.writeln("Saving TIFF 16-bit to " + fileRef.fsName);
    activeDocument.saveAs(fileRef, tiffOptions, false, Extension.TIFF);
    $.writeln("Saved TIFF: " + fileRef.fsName);
}

function getBaseName(name) {
    return name.replace(/\.[^.]+$/i, '');
}

function getErrorText(e) {
    if (!e) {
        return 'Unknown error';
    }

    var message = e.message || e.toString();
    if (e.line !== undefined) {
        message += ' (line ' + e.line + ')';
    }
    if (e.stack) {
        message += '\n' + e.stack;
    }
    return message;
}

main(startupArguments);