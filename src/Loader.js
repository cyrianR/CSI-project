function fetchDataLength(path, callback) {
    let xhr = new XMLHttpRequest();

    xhr.open('HEAD', path, true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                callback(xhr.getResponseHeader('Content-Length'));
            }
        }
    };
    xhr.send();
}

function fetchData(path, start, end, callback) {
    let xhr = new XMLHttpRequest();

    xhr.open('GET', path, true);
    xhr.setRequestHeader('Range', 'bytes=' + start + "-" + (end - 1));
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 206) {
                callback(xhr.responseText);
            }
        }
    };
    xhr.send();
}

function parseLine(line, number) {
    let element = {};
    let split = line.split('#')[0].split(/[ \t]+/);
    if (split.length === 0) {
        return;
    }

    switch (split[0]) {
        case "v":
            element.type = Element.AddVertex;
            element.value = new THREE.Vector3(
                parseFloat(split[1]),
                parseFloat(split[2]),
                parseFloat(split[3]),
            );
            return element;

        case "f":
            element.type = Element.AddFace;
            element.value = new THREE.Face3(
                parseInt(split[1], 10) - 1,
                parseInt(split[2], 10) - 1,
                parseInt(split[3], 10) - 1,
            );
            return element;

        case "fc":
            element.type = Element.SetFaceColor;
            element.id = parseInt(split[1], 10) - 1;
            element.value = new THREE.Color(
                parseFloat(split[2]),
                parseFloat(split[3]),
                parseFloat(split[4]),
            );
            return element;

        case "ts":
            element.type = Element.AddTriangleStrip;
            element.value = [];
            for (let i = 1; i < split.length - 2; i++) {
                element.value.push(new THREE.Face3(
                    parseInt(split[i]  , 10) - 1,
                    i % 2 === 1 ? parseInt(split[i+1], 10) - 1 : parseInt(split[i+2], 10) - 1,
                    i % 2 === 1 ? parseInt(split[i+2], 10) - 1 : parseInt(split[i+1], 10) - 1,
                ));
            }
            return element;

        case "tf":
            element.type = Element.AddTriangleFan;
            element.value = [];
            for (let i = 1; i < split.length - 2; i++) {
                element.value.push(new THREE.Face3(
                    parseInt(split[1]  , 10) - 1,
                    parseInt(split[i+1], 10) - 1,
                    parseInt(split[i+2], 10) - 1,
                ));
            }
            return element;

        case "ev":
            element.type = Element.EditVertex;
            element.id = parseInt(split[1], 10) - 1;
            element.value = new THREE.Vector3(
                parseFloat(split[2]),
                parseFloat(split[3]),
                parseFloat(split[4]),
            );
            return element;

        case "tv":
            element.type = Element.TranslateVertex;
            element.id = parseInt(split[1], 10) - 1;
            element.value = new THREE.Vector3(
                parseFloat(split[2]),
                parseFloat(split[3]),
                parseFloat(split[4]),
            );
            return element;

        case "pv":
            element.type = Element.PredictVertex;
            element.value = new THREE.Face3(
                parseInt(split[2], 10) - 1,
                parseInt(split[2], 10) - 1,
                parseInt(split[2], 10) - 1,
            );
            return element;

        case "efv":
            element.type = Element.EditFaceVertex;
            element.id = parseInt(split[1], 10) - 1;
            element.oldIndex = parseInt(split[2], 10) - 1;
            element.value = parseInt(split[3], 10) - 1;
            return element;

        case "ef":
            element.type = Element.EditFace;
            element.id = parseInt(split[1], 10) - 1;
            element.value = new THREE.Face3(
                parseInt(split[2], 10) - 1,
                parseInt(split[3], 10) - 1,
                parseInt(split[4], 10) - 1,
            );
            return element;

        case "df":
            element.type = Element.DeleteFace;
            element.id = parseInt(split[1], 10) - 1;
            return element;

        case "":
        case "#":
            return;

        default:
            return;
            // throw new Error(split[0] + " is not a defined macro in line " + number);
    }

}

const Element = {};
Element.AddVertex = "AddVertex";
Element.AddFace = "AddFace";
Element.AddTriangleStrip = "AddTriangleStrip";
Element.AddTriangleFan = "AddTriangleFan";
Element.EditVertex = "EditVertex";
Element.EditFace = "EditFace";
Element.EditFaceVertex = "EditFaceVertex";
Element.TranslateVertex = "TranslateVertex";
Element.DeleteFace = "DeleteFace";
Element.SetFaceColor = "SetFaceColor";
Element.PredictVertex = "PredictVertex";

class Loader {
    constructor(path, chunkSize = 1024, timeout = 20) {
        this.path = path;
        this.chunkSize = chunkSize;
        this.timeout = timeout;
        this.currentByte = 0;
        this.remainder = "";
    }

    start(callback) {
        fetchDataLength(this.path, (length) => {
            this.dataLength = length;
            this.next(callback);
        });
    }

    percentage() {
        return 100 * this.currentByte / this.dataLength;
    }

    next(callback) {
        this.downloadAndParseNextChunk((data) => {
            callback(data);
            setTimeout(() => {
                this.next(callback);
            }, this.timeout);
        });
    }

    downloadAndParseNextChunk(callback) {

        let upperBound = Math.min(this.currentByte + this.chunkSize, this.dataLength);

        if (upperBound <= this.currentByte) {
            if (this.remainder !== "") {
                callback([parseLine(this.remainder, 0)]);
            }
            return;
        }

        fetchData(this.path, this.currentByte, upperBound, (data) => {

            this.currentByte = upperBound;

            let elements = [];
            let split = data.split('\n');
            split[0] = this.remainder + split[0];
            this.remainder = split.pop();

            for (let i = 0; i < split.length; i++) {
                elements.push(parseLine(split[i], i));
            }

            callback(elements);

        });
    }
}
