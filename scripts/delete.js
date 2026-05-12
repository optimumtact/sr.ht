function remove(target) {
    var p = target.parentElement.parentElement;
    p.parentElement.removeChild(p);
}

var rejects = document.querySelectorAll(".delete");
for (var i = 0; i < rejects.length; i++) {
    rejects[i].addEventListener("click", function(e) {
        e.preventDefault();
        e.preventDefault();
        var filename = e.target.dataset.filename;
        var xhr = new XMLHttpRequest();
        xhr.onload = function() {
            var response = JSON.parse(xhr.responseText);
            if(response.success) {
                remove(e.target)
            }
        };
        xhr.open("POST", "/api/delete");
        var form = new FormData();
        form.append("key", window.api_key);
        form.append("filename", filename);
        xhr.send(form);
    });
}
