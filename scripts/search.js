document.addEventListener("DOMContentLoaded", function () {
  const searchForm = document.getElementById("search-form");
  const searchQuery = document.getElementById("search-query");
  const gallery = document.querySelector(".gallery");
  const paginationDivs = document.querySelectorAll(".pagination");
  const h4 = document.querySelector("h4");

  let currentQuery = "";

  function attachDeleteListeners() {
    var rejects = document.querySelectorAll(".delete");
    for (var i = 0; i < rejects.length; i++) {
        rejects[i].addEventListener("click", function(e) {
            e.preventDefault();
            var filehash = e.target.dataset.filehash;
            var xhr = new XMLHttpRequest();
            xhr.onload = function() {
                var response = JSON.parse(xhr.responseText);
                if(response.success) {
                    var p = e.target.parentElement.parentElement;
                    p.parentElement.removeChild(p);
                }
            };
            xhr.open("POST", "/api/delete");
            var form = new FormData();
            form.append("key", window.api_key);
            form.append("filehash", filehash);
            xhr.send(form);
        });
    }
  }

  attachDeleteListeners();

  function renderResults(data) {
    gallery.innerHTML = "";
    if (data.results.length === 0) {
      gallery.innerHTML = "<p>No results found.</p>";
      h4.innerText = "My Uploads";
      return;
    }

    h4.innerText = `My Uploads - showing ${data.results.length} results for "${currentQuery}" on page ${data.pagination.page} of ${data.pagination.pages}`;

    data.results.forEach((upload) => {
      const div = document.createElement("div");
      div.innerHTML = `
        <a href="${upload.url}"><img class="${
        upload.thumbnail ? "normal" : "missing"
      }" src="${upload.thumbnail}"></a>
        <div class="imageattribute">
            ${upload.original_name}
        </div>
        <div class="imageattribute">
            Uploaded: ${new Date(upload.created).toLocaleDateString()}
        </div>
        <div>
            <a href="#" class="btn btn-sm btn-danger delete" data-filehash="${
              upload.filehash
            }">delete</a>
        </div>
      `;
      gallery.appendChild(div);
    });
  }

  function renderPagination(pagination) {
    paginationDivs.forEach((paginationDiv) => {
      paginationDiv.innerHTML = "";
      if (pagination.pages <= 1) {
        return;
      }

      if (pagination.has_prev) {
        const prev = document.createElement("span");
        prev.innerHTML = `<a class='page-number pagination-prev' href="#">&lt;&lt;&lt;</a>`;
        prev.querySelector("a").addEventListener("click", (e) => {
          e.preventDefault();
          performSearch(currentQuery, pagination.page - 1);
        });
        paginationDiv.appendChild(prev);
      }

      for (let i = 1; i <= pagination.pages; i++) {
        const pageLink = document.createElement("span");
        if (i === pagination.page) {
          pageLink.innerHTML = `<a class='page-number pagination-item pagination-active' href="#">${i}</a>`;
        } else {
          pageLink.innerHTML = `<a class='page-number pagination-item' href="#">${i}</a>`;
        }
        pageLink.querySelector("a").addEventListener("click", (e) => {
          e.preventDefault();
          performSearch(currentQuery, i);
        });
        paginationDiv.appendChild(pageLink);
      }

      if (pagination.has_next) {
        const next = document.createElement("span");
        next.innerHTML = `<a class='page-number pagination-next' href="#">&gt;&gt;&gt;</a>`;
        next.querySelector("a").addEventListener("click", (e) => {
          e.preventDefault();
          performSearch(currentQuery, pagination.page + 1);
        });
        paginationDiv.appendChild(next);
      }
    });
  }

  function performSearch(query, page) {
    fetch(`/api/uploads/search?q=${query}&page=${page}`)
      .then((response) => response.json())
      .then((data) => {
        renderResults(data);
        renderPagination(data.pagination);
        attachDeleteListeners();
      });
  }

  searchForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const query = searchQuery.value;
    if (!query) {
      window.location.reload();
      return;
    }
    currentQuery = query;
    performSearch(query, 1);
  });
});