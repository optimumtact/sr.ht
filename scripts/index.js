var paste = document.getElementById("paste");
var pasteBtn = document.getElementById("paste-btn");
var browse = document.getElementById('browse');

window.addEventListener('dragenter', dragNOP, false);
window.addEventListener('dragleave', dragNOP, false);
window.addEventListener('dragover', dragNOP, false);
window.addEventListener('drop', handleDragDrop, false);

document.querySelector(".target").addEventListener("click", function(e) {
    e.preventDefault();
    browse.click();
});

browse.addEventListener("change", function(e) {
    for (var i = 0; i < browse.files.length; i++) {
        var f = browse.files[i];
        var progress = addRow(f);
        uploadFile(f, progress);
    }
});

document.getElementById("reset-key").addEventListener("click", function(e) {
    e.target.setAttribute("disabled", "disabled");
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/resetkey");
    xhr.onload = function() {
        e.target.removeAttribute("disabled");
        var key = JSON.parse(xhr.responseText).key;
        var keys = document.querySelectorAll(".apikey");
        for (var i = 0; i < keys.length; i++) {
            keys[i].textContent = key;
        }
        document.getElementById("syntaxKey").innerHTML =
            "curl \\\n    -F key=" + key + " \\\n    -F file=@example.png \\\n    " + window.root + "/api/upload";
        window.api_key = key;
        var q = document.getElementById("qrcode");
        q.innerHTML = "";
        new QRCode(q, "srht:" + window.location.hostname + ":" + window.api_key);
    };
    var form = new FormData();
    form.append("key", window.api_key);
    xhr.send(form);
});

function addRow(file) {
    var row = document.createElement("tr");
    var name = document.createElement("td");
    name.textContent = file.name;
    var progressCell = document.createElement("td");
    var progress = document.createElement("div");
    progressCell.appendChild(progress);
    progress.className = "progress";
    var progressBar = document.createElement("div");
    progressBar.style.width = "0%";
    progressBar.textContent = "0%";
    progressBar.className = "progress-bar";
    progress.appendChild(progressBar);
    row.appendChild(name);
    row.appendChild(progressCell);
    document.getElementById("files").appendChild(row);
    return progressCell;
}

function dragNOP(e) {
    e.stopPropagation();
    e.preventDefault();
}

function handleDragDrop(e) {
    dragNOP(e);
    for (var i = 0; i < e.dataTransfer.files.length; i++) {
        var file = e.dataTransfer.files[i];
        var progress = addRow(file);
        uploadFile(file, progress);
    }
}

paste.addEventListener("keydown", function() {
    pasteBtn.style.display = 'block';
});
pasteBtn.addEventListener("click", function(e) {
    e.preventDefault();
    var blob = new Blob([paste.value], {type: "text/plain"});
    var file = new File([blob], "paste.txt");
    var progress = addRow(file);
    uploadFile(file, progress);
});

function uploadFile(file, progress) {
    var bar = progress.querySelector(".progress-bar");
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload");
    console.log('Hello world yo');
    xhr.onload = function() {
        var response = JSON.parse(xhr.responseText);
        progress.innerHTML = "<a href='" + response.url + "'>" + response.url + "</a>";
    };
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            var progress = Math.floor((e.loaded / e.total) * 100);
            bar.style.width = progress + "%";
            bar.textContent = progress + "%";
        }
    };
    var form = new FormData();
    form.append("key", window.api_key);
    form.append("file", file);
    xhr.send(form);
}

new QRCode(document.getElementById("qrcode"), "srht:" + window.location.hostname + ":" + window.api_key);
