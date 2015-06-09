var approves = document.querySelectorAll(".approve");
for (var i = 0; i < approves.length; i++) {
    approves[i].addEventListener("click", function(e) {
        e.preventDefault();
        var id = e.target.dataset.user;
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/approve/" + id);
        xhr.send();
    });
}

var rejects = document.querySelectorAll(".reject");
for (var i = 0; i < rejects.length; i++) {
    rejects[i].addEventListener("click", function(e) {
        e.preventDefault();
        var id = e.target.dataset.user;
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/reject/" + id);
        xhr.send();
    });
}
