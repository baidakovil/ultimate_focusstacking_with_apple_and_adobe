app.bringToFront();

var startupArguments = (typeof arguments !== 'undefined') ? arguments : [];

function main(args) {
    var folderPath = args && args.length > 0 ? args[0] : null;
    var result = runFocusStacking(folderPath);
    return "Focus stacking completed: " + result;
}

function runFocusStacking(folderPath) {
    var mainFolder = resolveInputFolder(folderPath);
    if (!mainFolder) {
        return "Error: No folder selected";
    }

    var folders = getSubfolders(mainFolder);
    var processedFolders = 0;

    for (var i = 0; i < folders.length; i++) {
        var currentFolder = folders[i];
        if (currentFolder instanceof Folder) {
            processFolder(currentFolder, mainFolder);
            processedFolders++;
        }
    }

    return "Success: Processed " + processedFolders + " folder(s) for focus stacking";
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

function processFolder(selectedFolder, outputFolder) {
    if (!selectedFolder) {
        return;
    }

    var imageFiles = selectedFolder.getFiles(/\.(jpg|jpe|jpeg|dng|bmp|tif|tiff|psd|crw|cr2|exr|pcx|nef|dcr|dc2|erf|raf|orf|tga|mos|pef|png)$/i);
    if (!imageFiles || imageFiles.length < 2) {
        return;
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

        var baseName = getBaseName(activeDocument.activeLayer.name);
        var outputFile = new File(outputFolder + '/' + baseName + '_fs.jpg');
        saveAsJpeg(outputFile);
        app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
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

    activeDocument.saveAs(fileRef, jpgOptions, true, Extension.LOWERCASE);
}

function getBaseName(name) {
    return name.replace(/\.[^.]+$/i, '');
}

main(startupArguments);